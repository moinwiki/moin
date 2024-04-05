# Copyright: 2008 MoinMoin:ThomasWaldmann
# Copyright: 2010 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - moin.auth.ldap Tests
"""


import pytest


from moin._tests.ldap_testbase import LDAPTstBase, LdapEnvironment, check_environ, SLAPD_EXECUTABLE
from moin._tests.ldap_testdata import BASEDN, LDIF_CONTENT, ROOTDN, ROOTPW, SLAPD_CONFIG
from moin._tests import wikiconfig
from moin.auth import handle_login

msg = check_environ()
if msg:
    pytestmark = pytest.mark.skip(msg)
del msg

ldap = pytest.importorskip("ldap")


class TestLDAPServer(LDAPTstBase):
    basedn = BASEDN
    rootdn = ROOTDN
    rootpw = ROOTPW
    slapd_config = SLAPD_CONFIG
    ldif_content = LDIF_CONTENT

    def testLDAP(self):
        """Just try accessing the LDAP server and see if usera and userb are in LDAP."""
        server_uri = self.ldap_env.slapd.url
        base_dn = self.ldap_env.basedn
        lo = ldap.initialize(server_uri)
        ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)  # ldap v2 is outdated
        lo.simple_bind_s("", "")
        lusers = lo.search_st(base_dn, ldap.SCOPE_SUBTREE, "(uid=*)")
        uids = [ldap_dict["uid"][0] for dn, ldap_dict in lusers]
        assert b"usera" in uids
        assert b"userb" in uids


class TestMoinLDAPLogin(LDAPTstBase):
    basedn = BASEDN
    rootdn = ROOTDN
    rootpw = ROOTPW
    slapd_config = SLAPD_CONFIG
    ldif_content = LDIF_CONTENT

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            from moin.auth.ldap_login import LDAPAuth

            # ToDo get these vars from the test environment
            server_uri = "ldap://127.0.0.1:3890"
            base_dn = "ou=testing,dc=example,dc=org"
            ldap_auth1 = LDAPAuth(server_uri=server_uri, base_dn=base_dn, autocreate=True)
            auth = [ldap_auth1]

        return Config

    def testMoinLDAPLogin(self):
        """Just try accessing the LDAP server and see if usera and userb are in LDAP."""

        # tests that must not authenticate:
        u = handle_login(None, username="", password="")
        assert u is None
        u = handle_login(None, username="usera", password="")
        assert u is None
        u = handle_login(None, username="usera", password="userawrong")
        assert u is None
        u = handle_login(None, username="userawrong", password="usera")
        assert u is None

        # tests that must authenticate:
        u1 = handle_login(None, username="usera", password="usera")
        assert u1 is not None
        assert u1.valid

        u2 = handle_login(None, username="userb", password="userb")
        assert u2 is not None
        assert u2.valid

        # check if usera and userb have different ids:
        assert u1.profile["itemid"] != u2.profile["itemid"]


class TestBugDefaultPasswd(LDAPTstBase):
    basedn = BASEDN
    rootdn = ROOTDN
    rootpw = ROOTPW
    slapd_config = SLAPD_CONFIG
    ldif_content = LDIF_CONTENT

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            from moin.auth.ldap_login import LDAPAuth
            from moin.auth import MoinAuth

            # ToDo get these vars from the test environment
            server_uri = "ldap://127.0.0.1:3890"
            base_dn = "ou=testing,dc=example,dc=org"
            ldap_auth = LDAPAuth(server_uri=server_uri, base_dn=base_dn, autocreate=True)
            moin_auth = MoinAuth()
            auth = [ldap_auth, moin_auth]

        return Config

    def teardown_class(self):
        """Stop slapd, remove LDAP server environment"""
        self.ldap_env.stop_slapd()
        self.ldap_env.destroy_env()

    def testBugDefaultPasswd(self):
        """Login via LDAP (this creates user profile and up to 1.7.0rc1 it put
        a default password there), then try logging in via moin login using
        that default password or an empty password.
        """
        # do a LDAPAuth login (as a side effect, this autocreates the user profile):
        u1 = handle_login(None, username="usera", password="usera")
        assert u1 is not None
        assert u1.valid

        # now we kill the LDAP server:
        # self.ldap_env.slapd.stop()

        # now try a MoinAuth login:
        # try the default password that worked in 1.7 up to rc1:
        u2 = handle_login(None, username="usera", password="{SHA}NotStored")
        assert u2 is None

        # try using no password:
        u2 = handle_login(None, username="usera", password="")
        assert u2 is None

        # try using wrong password:
        u2 = handle_login(None, username="usera", password="wrong")
        assert u2 is None


class TestTwoLdapServers:
    basedn = BASEDN
    rootdn = ROOTDN
    rootpw = ROOTPW
    slapd_config = SLAPD_CONFIG
    ldif_content = LDIF_CONTENT

    def setup_class(self):
        """Create LDAP servers environment, start slapds"""
        self.ldap_envs = []
        for instance in range(2):
            ldap_env = LdapEnvironment(self.basedn, self.rootdn, self.rootpw, instance=instance)
            ldap_env.create_env(slapd_config=self.slapd_config)
            started = ldap_env.start_slapd()
            if not started:
                pytest.skip(
                    "Failed to start {} process, please see your syslog / log files"
                    " (and check if stopping apparmor helps, in case you use it).".format(SLAPD_EXECUTABLE)
                )
            ldap_env.load_directory(ldif_content=self.ldif_content)
            self.ldap_envs.append(ldap_env)

    def teardown_class(self):
        """Stop slapd, remove LDAP server environment"""
        for ldap_env in self.ldap_envs:
            ldap_env.stop_slapd()
            ldap_env.destroy_env()

    def testLDAP(self):
        """Just try accessing the LDAP servers and see if usera and userb are in LDAP."""
        for ldap_env in self.ldap_envs:
            server_uri = ldap_env.slapd.url
            base_dn = ldap_env.basedn
            lo = ldap.initialize(server_uri)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)  # ldap v2 is outdated
            lo.simple_bind_s("", "")
            lusers = lo.search_st(base_dn, ldap.SCOPE_SUBTREE, "(uid=*)")
            uids = [ldap_dict["uid"][0] for dn, ldap_dict in lusers]
            assert b"usera" in uids
            assert b"userb" in uids


class TestLdapFailover:
    basedn = BASEDN
    rootdn = ROOTDN
    rootpw = ROOTPW
    slapd_config = SLAPD_CONFIG
    ldif_content = LDIF_CONTENT

    def setup_class(self):
        """Create LDAP servers environment, start slapds"""
        self.ldap_envs = []
        for instance in range(2):
            ldap_env = LdapEnvironment(self.basedn, self.rootdn, self.rootpw, instance=instance)
            ldap_env.create_env(slapd_config=self.slapd_config)
            started = ldap_env.start_slapd()
            if not started:
                pytest.skip(
                    "Failed to start {} process, please see your syslog / log files"
                    " (and check if stopping apparmor helps, in case you use it).".format(SLAPD_EXECUTABLE)
                )
            ldap_env.load_directory(ldif_content=self.ldif_content)
            self.ldap_envs.append(ldap_env)

    @pytest.fixture
    def cfg(self):
        class Config(wikiconfig.Config):
            from moin.auth.ldap_login import LDAPAuth

            # ToDo get these vars from the test environment
            server_uri = "ldap://127.0.0.1:3891"
            base_dn = "ou=testing,dc=example,dc=org"
            ldap_auth1 = LDAPAuth(server_uri=server_uri, base_dn=base_dn, name="ldap1", autocreate=True, timeout=1)
            # short timeout, faster testing
            server_uri = "ldap://127.0.0.1:3892"
            ldap_auth2 = LDAPAuth(server_uri=server_uri, base_dn=base_dn, name="ldap2", autocreate=True, timeout=1)
            auth = [ldap_auth1, ldap_auth2]

        return Config

    def teardown_class(self):
        """Stop slapd, remove LDAP server environment"""
        for ldap_env in self.ldap_envs:
            try:
                ldap_env.stop_slapd()
            except:  # noqa
                pass  # one will fail, because it is already stopped
            ldap_env.destroy_env()

    def testMoinLDAPFailOver(self):
        """Try if it does a failover to a secondary LDAP, if the primary fails."""

        # authenticate user (with primary slapd):
        u1 = handle_login(None, username="usera", password="usera")
        assert u1 is not None
        assert u1.valid

        # now we kill our primary LDAP server:
        self.ldap_envs[0].slapd.stop()

        # try if we can still authenticate (with the second slapd):
        u2 = handle_login(None, username="usera", password="usera")
        assert u2 is not None
        assert u2.valid
