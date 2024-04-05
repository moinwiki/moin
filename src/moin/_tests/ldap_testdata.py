# Copyright: 2008 MoinMoin:ThomasWaldmann
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - LDAP test data
"""


BASEDN = "ou=testing,dc=example,dc=org"
ROOTDN = f"cn=root,{BASEDN}"
ROOTPW = "secret"

SLAPD_CONFIG = """\
# See slapd.conf(5) for details on configuration options.

include %(schema_dir)s/core.schema
include %(schema_dir)s/cosine.schema
include %(schema_dir)s/inetorgperson.schema
#include %(schema_dir)s/misc.schema

moduleload back_bdb.la

threads 2

# Global access control ###############################################

# Root DSE: allow anyone to read it
access to dn.base="" by * read
# Subschema (sub)entry DSE: allow anyone to read it
access to dn.base="cn=Subschema" by * read

# we don't need restrictive ACLs for tests:
access to * by * read

allow bind_anon_dn

# Test-Datenbank ou=testing,dc=example,dc=org ################

database bdb

directory %(ldap_db_dir)s
suffix "%(basedn)s"
rootdn "%(rootdn)s"
rootpw %(rootpw)s
lastmod on

index uid eq

checkpoint 200 5

# Entries to cache in memory
cachesize 500
# Search results to cache in memory
idlcachesize 50

sizelimit -1
"""

LDIF_CONTENT = """\
########################################################################
# regression testing
########################################################################
version: 1

dn: ou=testing,dc=example,dc=org
objectClass: organizationalUnit
ou: testing

dn: ou=Groups,ou=testing,dc=example,dc=org
objectClass: organizationalUnit
ou: Groups

dn: ou=Users,ou=testing,dc=example,dc=org
objectClass: organizationalUnit
ou: Users

dn: ou=Unit A,ou=Users,ou=testing,dc=example,dc=org
objectClass: organizationalUnit
ou: Unit A

dn: ou=Unit B,ou=Users,ou=testing,dc=example,dc=org
objectClass: organizationalUnit
ou: Unit B

dn: uid=usera,ou=Unit A,ou=Users,ou=testing,dc=example,dc=org
objectClass: account
objectClass: simpleSecurityObject
uid: usera
# this is md5 encoded 'usera' for password
userPassword: {MD5}aXqgOSc5gSW7YoLi9BSmvg==

dn: uid=userb,ou=Unit B,ou=Users,ou=testing,dc=example,dc=org
cn: Vorname Nachname
objectClass: inetOrgPerson
sn: Nachname
uid: userb
# this is md5 encoded 'userb' for password
userPassword: {MD5}ThvfQsM7OQFjqSUQOX2XsA==

dn: cn=Group A,ou=Groups,ou=testing,dc=example,dc=org
cn: Group A
member: cn=dummy
member: uid=usera,ou=Unit A,ou=Users,ou=testing,dc=example,dc=org
objectClass: groupOfNames

dn: cn=Group B,ou=Groups,ou=testing,dc=example,dc=org
cn: Group B
objectClass: groupOfUniqueNames
uniqueMember: cn=dummy
uniqueMember: uid=userb,ou=Unit B,ou=Users,ou=testing,dc=example,dc=org

dn: cn=Group C,ou=Groups,ou=testing,dc=example,dc=org
cn: Group C
description: Nested group!
member: cn=dummy
member: cn=Group A,ou=Groups,ou=testing,dc=example,dc=org
objectClass: groupOfNames
"""
