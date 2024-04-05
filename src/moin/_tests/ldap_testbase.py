# Copyright: 2008 by Thomas Waldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    LDAPTestBase: LDAP testing support for pytest based unit tests

    Features
    --------

    * setup_class
      * automatic creation of a temporary LDAP server environment
      * automatic creation of a LDAP server process (slapd)

    * teardown_class
      * LDAP server process will be killed and termination will be waited for
      * temporary LDAP environment will be removed

    Usage
    -----

    Write your own test class and derive from LDAPTestBase:

    class TestLdap(LDAPTestBase):
        def testFunction(self):
            server_url = self.ldap_env.slapd.url
            lo = ldap.initialize(server_url)
            lo.simple_bind_s('', '')

    Notes
    -----

    On Ubuntu 8.04 there is apparmor imposing some restrictions on /usr/sbin/slapd,
    so you need to disable apparmor by invoking this as root:

    # /etc/init.d/apparmor stop
"""


import os
import shutil
import tempfile
import time
import base64
from io import StringIO
import signal
import subprocess
import hashlib

try:
    # needs python-ldap
    import ldap
    import ldap.modlist
    import ldif
except ImportError:
    ldap = None


# filename of LDAP server executable - if it is not
# in your PATH, you have to give full path/filename.
SLAPD_EXECUTABLE = "slapd"


def check_environ():
    """Check the system environment whether we are able to run.
    Either return some failure reason if we can't or None if everything
    looks OK.
    """
    if ldap is None:
        return "You need python-ldap installed to use ldap_testbase."
    slapd = False
    try:
        p = subprocess.Popen([SLAPD_EXECUTABLE, "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pid = p.pid
        rc = p.wait()
        if pid and rc == 1:
            slapd = True  # it works
    except OSError as err:
        import errno

        if not (err.errno == errno.ENOENT or (err.errno == 3 and os.name == "nt")):
            raise
    if not slapd:
        return f"Can't start {SLAPD_EXECUTABLE} (see SLAPD_EXECUTABLE)."
    return None


class Slapd:
    """Manage a slapd process for testing purposes"""

    def __init__(
        self,
        config=None,  # config filename for -f
        executable=SLAPD_EXECUTABLE,
        debug_flags="",  # None,  # for -d stats,acl,args,trace,sync,config
        proto="ldap",
        ip="127.0.0.1",
        port=3890,  # use -h proto://ip:port
        service_name="",  # defaults to -n executable:port, use None to not use -n
    ):
        self.executable = executable
        self.config = config
        self.debug_flags = debug_flags
        self.proto = proto
        self.ip = ip
        self.port = port
        self.url = f"{proto}://{ip}:{port}"  # can be used for ldap.initialize() call
        if service_name == "":
            self.service_name = f"{executable}:{port}"
        else:
            self.service_name = service_name

    def start(self, timeout=0):
        """start a slapd process and optionally wait up to timeout seconds until it responds"""
        args = [self.executable, "-h", self.url]
        if self.config is not None:
            args.extend(["-f", self.config])
        if self.debug_flags is not None:
            args.extend(["-d", self.debug_flags])
        if self.service_name:
            args.extend(["-n", self.service_name])
        self.process = subprocess.Popen(args)
        started = None
        if timeout:
            lo = ldap.initialize(self.url)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)  # ldap v2 is outdated
            started = False
            wait_until = time.time() + timeout
            while time.time() < wait_until:
                try:
                    lo.simple_bind_s("", "")
                    started = True
                except ldap.SERVER_DOWN:
                    time.sleep(0.1)
                else:
                    break
        return started

    def stop(self):
        """stop this slapd process and wait until it has terminated"""
        pid = self.process.pid
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, 0)


class LdapEnvironment:
    """Manage a (temporary) environment for running a slapd in it"""

    # default DB_CONFIG bdb configuration file contents
    DB_CONFIG = """\
# STRANGE: if i use those settings, after the test slapd goes to 100% and doesn't terminate on SIGTERM
# Set the database in memory cache size.
#set_cachesize 0 10000000 1

# Set log values.
#set_lg_regionmax 262144
#set_lg_bsize 262144
#set_lg_max 10485760

#set_tas_spins 0
"""

    def __init__(
        self,
        basedn,
        rootdn,
        rootpw,
        instance=0,  # use different values when running multiple LdapEnvironments
        schema_dir="/etc/ldap/schema",  # directory with schemas
        coding="utf-8",  # coding used for config files
        timeout=10,  # how long to wait for slapd starting [s]
    ):
        self.basedn = basedn
        self.rootdn = rootdn
        self.rootpw = rootpw
        self.instance = instance
        self.schema_dir = schema_dir
        self.coding = coding
        self.ldap_dir = None
        self.slapd_conf = None
        self.timeout = timeout

    def create_env(self, slapd_config, db_config=DB_CONFIG):
        """create a temporary LDAP server environment in a temp. directory,
        including writing a slapd.conf (see configure_slapd) and a
        DB_CONFIG there.
        """
        # create directories
        self.ldap_dir = tempfile.mkdtemp(prefix=f"LdapEnvironment-{self.instance}.")
        self.ldap_db_dir = os.path.join(self.ldap_dir, "db")
        os.mkdir(self.ldap_db_dir)

        # create DB_CONFIG for bdb backend
        db_config_fname = os.path.join(self.ldap_db_dir, "DB_CONFIG")
        f = open(db_config_fname, "w")
        f.write(db_config)
        f.close()

        hash_pw = hashlib.new("md5", self.rootpw.encode(self.coding))
        rootpw = "{MD5}" + base64.b64encode(hash_pw.digest()).decode()

        # create slapd.conf from content template in slapd_config
        slapd_config = slapd_config % {
            "ldap_dir": self.ldap_dir,
            "ldap_db_dir": self.ldap_db_dir,
            "schema_dir": self.schema_dir,
            "basedn": self.basedn,
            "rootdn": self.rootdn,
            "rootpw": rootpw,
        }
        self.slapd_conf = os.path.join(self.ldap_dir, "slapd.conf")
        with open(self.slapd_conf, "w", encoding=self.coding) as f:
            f.write(slapd_config)

    def start_slapd(self):
        """start a slapd and optionally wait until it talks with us"""
        self.slapd = Slapd(config=self.slapd_conf, port=3890 + self.instance)
        started = self.slapd.start(timeout=self.timeout)
        return started

    def load_directory(self, ldif_content):
        """load the directory with the ldif_content (str)"""
        lo = ldap.initialize(self.slapd.url)
        ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)  # ldap v2 is outdated
        lo.simple_bind_s(self.rootdn, self.rootpw)

        class LDIFLoader(ldif.LDIFParser):
            def handle(self, dn, entry):
                lo.add_s(dn, ldap.modlist.addModlist(entry))

        loader = LDIFLoader(StringIO(ldif_content))
        loader.parse()

    def stop_slapd(self):
        """stop a slapd"""
        self.slapd.stop()

    def destroy_env(self):
        """remove the temporary LDAP server environment"""
        shutil.rmtree(self.ldap_dir)


try:
    import pytest

    class LDAPTstBase:
        """Test base class for pytest based tests which need a LDAP server to talk to.

        Inherit your test class from this base class to test LDAP stuff.
        """

        # You MUST define these in your derived class:
        slapd_config = None  # a string with your slapd.conf template
        ldif_content = None  # a string with your ldif contents
        basedn = None  # your base DN
        rootdn = None  # root DN
        rootpw = None  # root password

        def setup_class(self):
            """Create LDAP server environment, start slapd"""
            self.ldap_env = LdapEnvironment(self.basedn, self.rootdn, self.rootpw)
            self.ldap_env.create_env(slapd_config=self.slapd_config)
            started = self.ldap_env.start_slapd()
            if not started:
                pytest.skip(
                    "Failed to start {} process, please see your syslog / log files"
                    " (and check if stopping apparmor helps, in case you use it).".format(SLAPD_EXECUTABLE)
                )
            self.ldap_env.load_directory(ldif_content=self.ldif_content)

        def teardown_class(self):
            """Stop slapd, remove LDAP server environment"""
            self.ldap_env.stop_slapd()
            self.ldap_env.destroy_env()

except ImportError:
    pass  # obviously pytest not in use
