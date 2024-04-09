# Copyright: 2019 MoinMoin:RogerHaase
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Create sqlite3 data models for edit locking and saving drafts. Expected usage
is limited to the +modify method in /items/__init__.py for text items.

Moin2 has only two states for the edit_locking_Policy: None and 'lock'.
None is suitable for single user desktop wikis.

Drafts are always saved when an editor clicks the Preview link.
Regardless of the edit_locking_policy, warning messages are given to the
user when conflicts occur. Conflicts are caused when a user's edit lock times
out, a second user obtains the item's edit lock and saves the item with updates, and then
the first editor saves the item with conflicting updates. Such instances are
detected and warning messages are flashed and included in the saved item.

There are two small tables within the db saved in /wiki/sql/:
    * editlock - maintains state of edit locks on text items when the locking policy is lock.
        * there will be 1 row for each text item being actively edited or abandoned without a Save or Cancel
        * rows for abandoned edits will be reused if a second user edits the item
    * editdraft - saves pointers to text draft when user clicks the Preview button
        * there will be 1 row per user who has clicked Modify and has not yet Saved or Cancelled
        * if a user clicks Preview while editing a second item, the users old draft will be
          deleted and the row reused to point to the new draft

The preview drafts are saved in the /wiki/preview/ directory.

To stress test edit locking use the Locust based tests in /contrib/loadtesting/.
"""

import os
import time
import sqlite3

from flask import request
from flask import g as flaskg
from flask import current_app as app

from moin.i18n import L_
from moin.utils.mime import Type
from moin.constants.misc import ANON, NO_LOCK, LOCKED, LOCK
from moin.constants.keys import ITEMID, REVID, REV_NUMBER, NAME
from moin.utils import show_time

from moin import log

logging = log.getLogger(__name__)


# these are used to create paths to the sql database and saved drafts
SQL = "sql"
DB_NAME = "edit_utils.db"
PREVIEW = "preview"


class Edit_Utils:
    """
    Provide edit locking and save preview draft functions. Edit locking is optional, see wikiconfig.

    An instance of Edit_Utils is added to flaskg near the start of every +modify transaction.
    The instance has an open db connection that will be closed within the transaction teardown.
    """

    def __init__(self, item):
        self.item = item
        self.user_name = self.get_user_name()
        self.item_name = ",".join(item.names)
        # new items will not have rev_number, revid, nor itemid
        self.rev_number = item.meta.get(REV_NUMBER, 0)
        self.rev_id = item.meta.get(REVID, "new-item")
        self.item_id = item.meta.get(ITEMID, item.meta.get(NAME)[0])

        self.coding = "utf-8"
        contenttype = self.item.meta.get("contenttype", None)
        if contenttype is not None:
            ct = Type(contenttype)
            self.coding = ct.parameters.get("charset", self.coding)

        self.sql_filename = os.path.join(app.cfg.instance_dir, SQL, DB_NAME)
        if os.path.exists(self.sql_filename):
            self.conn = sqlite3.connect(self.sql_filename)
        else:
            self.conn = self.create_db_tables()
        self.cursor = self.conn.cursor()
        self.preview_path = os.path.join(app.cfg.instance_dir, PREVIEW)
        self.draft_name = self.make_draft_name(self.rev_id)

        self.conn.isolation_level = "EXCLUSIVE"
        self.conn.execute("BEGIN EXCLUSIVE")

    def create_db_tables(self):
        """
        Creates the SQLite3 database and tables used for saving edit drafts and edit locking.

        The edit locking table is created even if locking policy is None. A wiki admin can later
        change locking policy without affecting saved drafts.
        """
        if not os.path.exists(os.path.join(app.cfg.instance_dir, SQL)):
            os.mkdir(os.path.join(app.cfg.instance_dir, SQL))
        if not os.path.exists(os.path.join(app.cfg.instance_dir, PREVIEW)):
            os.mkdir(os.path.join(app.cfg.instance_dir, PREVIEW))
        con = sqlite3.connect(self.sql_filename)  # opens existing file or creates new file
        cursor = con.cursor()
        cursor.execute(
            """CREATE TABLE editlock(item_id TEXT NOT NULL PRIMARY KEY,
                                                item_name TEXT,
                                                user_name TEXT,
                                                timeout FLOAT
                                                )
        """
        )
        cursor.execute(
            """
            CREATE TABLE editdraft(user_name TEXT NOT NULL PRIMARY KEY,
                                   item_id TEXT,
                                   item_name TEXT,
                                   rev_number INTEGER,
                                   save_time INTEGER,
                                   rev_id TEXT
                                   )
        """
        )
        con.commit()
        return con

    def cursor_close(self):
        """Call this to release cursor and avoid OperationalError: database is locked"""
        # on windows development server seems better to close conn rather than cursor
        self.conn.close()

    def make_draft_name(self, rev_id):
        """Return a file name consisting of rev_id + user_name."""
        keepchars = ("-", ".", "_")
        return os.path.join(
            self.preview_path,
            rev_id + "-" + "".join(c for c in self.user_name if c.isalnum() or c in keepchars).rstrip(),
        )

    def get_user_name(self):
        """Return user name or user IP address."""
        user_name = flaskg.user.name0
        if user_name == ANON:
            user_name = request.remote_user or request.remote_addr
        return user_name

    def put_draft(self, data_in, overwrite=True):
        """
        Only 1 item draft is saved per user. Most recent item draft overlays prior item draft.

        If no editdraft row exists, an editdraft row is created when the user clicks the Modify
        link. The row is updated when the user clicks Preview. The row is deleted when the
        user clicks Cancel or Save/OK. The row is overwritten if the user abandons the edit
        and clicks Modify for a different item.

        The rev_number field is used to detect conflicting updates where first user's edit times
        out, second user edits and saves, first user wakes up and does a save.
        """
        rev_id = self.rev_id
        draft_rev_number = self.rev_number
        draft, data = self.get_draft()
        if draft:
            # draft may be of this item or remnant of a prior abandoned edit
            u_name, i_id, i_name, rev_number, save_time, i_rev_id = draft
            if i_id == self.item_id:
                if not overwrite:
                    return
                # in case of timeout and update by someone else get rev_number from prior Preview
                draft_rev_number = rev_number  # XXX per line 1074 in __init__
                rev_id = i_rev_id
                self.draft_name = self.make_draft_name(rev_id)
            self.cursor.execute("""DELETE FROM editdraft WHERE user_name = ? """, (self.user_name,))
        if data_in:
            data_in = data_in.encode(self.coding)
            with open(self.draft_name, "wb") as f:
                f.write(data_in)
            save_time = int(time.time())
        else:
            save_time = 0  # indicates user is editing item but has not done a preview, no draft has been saved
        self.cursor.execute(
            """INSERT INTO editdraft(user_name, item_id, item_name, rev_number, save_time, rev_id)
                           VALUES(?,?,?,?,?,?)""",
            (self.user_name, self.item_id, self.item_name, draft_rev_number, save_time, rev_id),
        )
        self.conn.commit()

    def get_draft(self):
        """
        Return None, None if no draft available; else tuple of row fields, textarea data or None.

        If existing draft is for wrong item, log error and delete.
        """
        self.cursor.execute(
            """SELECT user_name, item_id, item_name, rev_number, save_time, rev_id FROM editdraft
               WHERE user_name=?""",
            (self.user_name,),
        )
        draft = self.cursor.fetchone()
        if draft:
            u_name, i_id, i_name, rev_number, save_time, rev_id = draft
            if i_id == self.item_id:
                if save_time:
                    self.draft_name = self.make_draft_name(rev_id)
                    try:
                        with open(self.draft_name, "rb") as f:
                            data = f.read()
                        data = data.decode(self.coding)
                        return draft, data
                    except OSError:
                        logging.error(f"User {u_name} failed to load draft for: {i_name}")
                        return draft, None
                else:
                    return draft, None
            else:
                # draft is of edit abandoned long ago
                self._delete_draft(save_time, rev_id)
        return None, None

    def delete_draft(self):
        """If there is a draft, delete draft file and editdraft row."""
        draft, data = self.get_draft()
        if draft:
            u_name, i_id, i_name, rev_number, save_time, rev_id = draft
            # self.draft_name may be a newer revision
            self._delete_draft(save_time, rev_id)

    def _delete_draft(self, save_time, rev_id):
        """Delete editdraft row and draft data."""
        if save_time:
            draft_name = self.make_draft_name(rev_id)
            try:
                os.remove(draft_name)
            except OSError:
                # draft file is created only when user does Preview
                logging.error(f"IOError when deleting draft named {draft_name} for user {self.user_name}")
        self.cursor.execute("""DELETE FROM editdraft WHERE user_name = ? """, (self.user_name,))
        self.conn.commit()

    # editlock methods start here
    def update_editlock(self):
        """Reset existing editlock, same user or different user is given the item lock."""
        timeout = int(time.time()) + app.cfg.edit_lock_time * 60
        self.cursor.execute(
            """UPDATE editlock SET timeout = ?, user_name = ? WHERE item_id = ? """,
            (timeout, self.user_name, self.item_id),
        )
        self.conn.commit()

    def get_lock_status(self):
        """Return lock status of item_id, either a row of editlock or None"""
        self.cursor.execute(
            """SELECT item_id, item_name, user_name, timeout FROM editlock WHERE item_id=?""", (self.item_id,)
        )
        locked = self.cursor.fetchone()
        return locked

    def lock_item(self):
        """
        Return True, None if lock policy is None. Return True, msg if item locked successfully,
        else return False, 'lock failed' message.
        """
        msg = None
        if app.cfg.edit_locking_policy == LOCK:
            locked = self.get_lock_status()
            if locked:
                # somebody has lock, may be current user or other user; lock may have timed out
                i_id, i_name, u_name, timeout = locked
                if u_name == self.user_name:
                    # it is locked by current user, we do not care if lock timed out
                    self.update_editlock()
                    return LOCKED, None
                wait_time = timeout - int(time.time())
                interval, number = show_time.duration(wait_time)
                if wait_time < 0.0:
                    # some other user's lock has timed out, give one-time alert user about potential future conflict,
                    msg = L_(
                        "Edit lock for {user_name} timed out {number} {interval} ago, click 'Cancel' "
                        "to yield more time, clicking 'Save' may require {user_name} to resolve conflicting edits."
                    ).format(user_name=u_name, number=number, interval=interval)
                    self.update_editlock()
                    self.put_draft(None)
                    return LOCKED, msg
                else:
                    # item is locked by somebody else, make current user wait
                    msg = L_("Item '{item_name}' is locked by {user_name}. Try again in {number} {interval}.").format(
                        item_name=i_name, user_name=u_name, number=number, interval=interval
                    )
                    return NO_LOCK, msg

            else:
                # item is not locked
                timeout = int(time.time()) + app.cfg.edit_lock_time * 60
                draft, data = self.get_draft()
                if draft:
                    u_name, i_id, i_name, rev_number, save_time, rev_id = draft
                    if self.rev_number > rev_number:
                        # current user timed out, then other user updated and saved
                        msg = L_(
                            "Someone else updated '{item_name}' after your edit lock timed out. "
                            "If you click 'Save', conflicting changes must be manually merged. "
                            "Click 'Cancel' to discard changes."
                        ).format(item_name=self.item_name)
                    self.cursor.execute(
                        """INSERT INTO editlock(item_id, item_name, user_name, timeout)
                                      VALUES(?,?,?,?)""",
                        (self.item_id, self.item_name, self.user_name, timeout),
                    )
                    self.conn.commit()
                    return LOCKED, msg
                # if no draft, preserve starting rev_number by creating entry without rev_id
                self.put_draft(None)

                self.cursor.execute(
                    """INSERT INTO editlock(item_id, item_name, user_name, timeout) VALUES(?,?,?,?)""",
                    (self.item_id, self.item_name, self.user_name, timeout),
                )
                self.conn.commit()
        return LOCKED, msg

    def unlock_item(self, cancel=False):
        """
        Return None if OK, else return 'locked by someone else' message.

        Called on Cancel and OK/save processing.
        """
        user_name = self.user_name
        locked = self.get_lock_status()
        if locked:
            i_id, i_name, u_name, timeout = locked
            if u_name == user_name:
                self.cursor.execute("""DELETE FROM editlock WHERE item_id = ? """, (self.item_id,))
                self.conn.commit()
                return
            elif not cancel:
                # bug: someone else has active edit lock, relock_item() should have been called prior to item save
                logging.error(f"User {user_name} tried to unlock item that was locked by someone else: {i_name}")
                msg = L_(
                    "Item '{item_name}' is locked by {user_name}. Edit lock error, "
                    "check Item History to verify no changes were lost."
                ).format(item_name=i_name, user_name=u_name)
                return msg
        if not cancel:
            # bug: there should have been a lock_item call prior to unlock call
            logging.error(f"User {user_name} tried to unlock item that was not locked: {self.item_name}")
