# Copyright: 2006-2008 MoinMoin:ThomasWaldmann
# Copyright: 2007 MoinMoin:JohannesBerg
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - auth plugin for (un)mounting a smb share

    (u)mount a SMB server's share for username (using username/password for
    authentication at the SMB server). This can be used if you need access
    to files on some share via the wiki, but needs more code to be useful.
"""


from moin.auth import BaseAuth, ContinueLogin

from moin import log

logging = log.getLogger(__name__)


class SMBMount(BaseAuth):
    """auth plugin for (un)mounting an smb share,
    this is a wrapper around mount.cifs -o <options> //server/share mountpoint

    See man mount.cifs for details.
    """

    def __init__(
        self,
        server,  # mount.cifs //server/share
        share,  # mount.cifs //server/share
        mountpoint_fn,  # function of username to determine the mountpoint, e.g.:
        # lambda username: '/mnt/wiki/%s' % username
        dir_user,  # username to get the uid that is used for mount.cifs -o uid=... (e.g. 'www-data')
        domain,  # mount.cifs -o domain=...
        dir_mode="0700",  # mount.cifs -o dir_mode=...
        file_mode="0600",  # mount.cifs -o file_mode=...
        iocharset="utf-8",  # mount.cifs -o iocharset=... (try 'iso8859-1' if default does not work)
        coding="utf-8",  # encoding used for username/password/cmdline (try 'iso8859-1' if default does not work)
        log="/dev/null",  # logfile for mount.cifs output
        **kw,
    ):
        super().__init__(**kw)
        self.server = server
        self.share = share
        self.mountpoint_fn = mountpoint_fn
        self.dir_user = dir_user
        self.domain = domain
        self.dir_mode = dir_mode
        self.file_mode = file_mode
        self.iocharset = iocharset
        self.log = log
        self.coding = coding

    def do_smb(self, username, password, login):
        logging.debug(f"login={login} logout={not login}: got name={username!r}")

        import os
        import pwd
        import subprocess

        web_username = self.dir_user
        web_uid = pwd.getpwnam(web_username)[2]  # XXX better just use current uid?

        mountpoint = self.mountpoint_fn(username)
        if login:
            cmd = (
                "sudo mount -t cifs -o user=%(user)s,domain=%(domain)s,uid=%(uid)d,dir_mode=%(dir_mode)s,file_mode="
                "%(file_mode)s,iocharset=%(iocharset)s //%(server)s/%(share)s %(mountpoint)s >>%(log)s 2>&1"
            )
        else:
            cmd = "sudo umount %(mountpoint)s >>%(log)s 2>&1"

        cmd = cmd % {
            "user": username,
            "uid": web_uid,
            "domain": self.domain,
            "server": self.server,
            "share": self.share,
            "mountpoint": mountpoint,
            "dir_mode": self.dir_mode,
            "file_mode": self.file_mode,
            "iocharset": self.iocharset,
            "log": self.log,
        }
        env = os.environ.copy()
        if login:
            try:
                if not os.path.exists(mountpoint):
                    os.makedirs(mountpoint)  # the dir containing the mountpoint must be writeable for us!
            except OSError:
                pass
            env["PASSWD"] = password.encode(self.coding)
        subprocess.call(cmd.encode(self.coding), env=env, shell=True)

    def login(self, user_obj, **kw):
        username = kw.get("username")
        password = kw.get("password")
        if user_obj and user_obj.valid:
            self.do_smb(username, password, True)
        return ContinueLogin(user_obj)

    def logout(self, user_obj, **kw):
        if user_obj and not user_obj.valid:
            self.do_smb(user_obj.name, None, False)
        return user_obj, True
