==========
Namespaces
==========

MoinMoin supports the use of multiple namespaces where each namespace may have a
unique backend or media type. For example, the default namespace could use the OS filesystem
for item storage and another namespace could use an SQL database.

 - an item in one namespace can readily include or transclude content from an item residing
   in another namespace.
 - it is not possible for an item to have an alias name referencing a different
   namespace.
 - it is not possible to rename an item into a different namespace.
 - it is not possible to use a namespace name as an item name in a different namespace.

See the namespace section within MoinMoin configuration for information on how to configure
namespaces.

URL layout
==========
``http://server/[NAMESPACE/][[@FIELD/]VALUE][/+VIEW]``

The above defines the URL layout, where uppercase terms are variables defined below and [] denotes optional segments.
It means: search for items where field ``FIELD`` has value ``VALUE`` in namespace ``NAMESPACE`` and apply the
view ``VIEW`` to it.

NAMESPACE
 Defines the namespace for looking up the item. NAMESPACE value ``all`` is the "namespace doesn't matter" identifier.
 It is used to access global views like global history, global tags etc.

FIELD
 Whoosh schema field to look up the VALUE (default: ``name_exact``, lookup by name).
 FIELD can be a unique identifier (``itemid``, ``revid``, ``name_exact``) or non-unique (e.g., ``tags``).

VALUE
 Value to search in the FIELD (default: the default root within that namespace). If the FIELD is non-unique,
 we show a list of items that have ``FIELD:VALUE``.

VIEW
 Used to select the intended view method (default: ``show``).

**Examples**:
 The following examples show how a URL can look, ``ns1`` and ``ns1/ns2`` are namespaces.

 - ``http://localhost:8080/Home``
 - ``http://localhost:8080/ns1/@tags/sometag``
 - ``http://localhost:8080/ns1/ns2``
 - ``http://localhost:8080/ns1/SomePage``
 - ``http://localhost:8080/+modify/ns1/ns2/SomePage``
 - ``http://localhost:8080/+delete/ns1/@itemid/37b73d2a6c154bb4ab993d0fb463219c``
 - ``http://localhost:8080/ns1/@itemid/37b73d2a6c154bb4ab993d0fb463219c``
