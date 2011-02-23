#############################################################################
### Page edit locking
#############################################################################

EDIT_LOCK_TIMESTAMP = "edit_lock_timestamp"
EDIT_LOCK_ADDR = "edit_lock_addr"
EDIT_LOCK_HOSTNAME = "edit_lock_hostname"
EDIT_LOCK_USERID = "edit_lock_userid"

EDIT_LOCK = (EDIT_LOCK_TIMESTAMP, EDIT_LOCK_ADDR, EDIT_LOCK_HOSTNAME, EDIT_LOCK_USERID)

def get_edit_lock(item):
    """
    Given an Item, get a tuple containing the timestamp of the edit-lock and the user.
    """
    for key in EDIT_LOCK:
        if not key in item:
            return (False, 0.0, "", "", "")
        else:
            return (True, float(item[EDIT_LOCK_TIMESTAMP]), item[EDIT_LOCK_ADDR],
                    item[EDIT_LOCK_HOSTNAME], item[EDIT_LOCK_USERID])

def set_edit_lock(item):
    """
    Set the lock property to True or False.
    """
    timestamp = time.time()
    addr = request.remote_addr
    hostname = wikiutil.get_hostname(addr)
    userid = flaskg.user.valid and flaskg.user.id or ''

    item.change_metadata()
    item[EDIT_LOCK_TIMESTAMP] = str(timestamp)
    item[EDIT_LOCK_ADDR] = addr
    item[EDIT_LOCK_HOSTNAME] = hostname
    item[EDIT_LOCK_USERID] = userid
    item.publish_metadata()


