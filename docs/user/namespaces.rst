==========
Namespaces
==========

URL layout
==========
``http://server/[NAMESPACE/][[@FIELD/]VALUE][/+VIEW]``

Above defines the URL layout, where uppercase letters are variable parts defined below and [] denotes optional.
It basically means search for the item field ``FIELD`` value ``VALUE`` in the namespace ``NAMESPACE`` and apply the 
view ``VIEW`` on it.

NAMESPACE
 Defines the namespace for looking up the item. NAMESPACE value ``all`` is the "namespace doesn't matter" identifier.
 It is used to access global views like global history, global tags etc.

FIELD
 Whoosh schema value where to lookup the VALUE. Default value for field is ``name_exact`` (search by name). FIELD can be a unique identifier like (``itemid, revid, name_exact``) or can be non-unique like (``tags``).

VALUE
 Value to search in the FIELD. The default value is the default root within that namespace. If the FIELD is non-unique, we
 show a list items which can have the ``FIELD value:VALUE``.

VIEW
 used to select the intended view method (default: ``show``).

**Examples**:
 The following examples show how a url can look like, ``ns1, ns1/ns2`` are namespaces.

 - ``http://localhost:8080/Home``
 - ``http://localhost:8080/ns1/@tags/sometag``
 - ``http://localhost:8080/ns1/ns2``
 - ``http://localhost:8080/ns1/SomePage``
 - ``http://localhost:8080/+modify/ns1/ns2/SomePage``
 - ``http://localhost:8080/+delete/ns1/@itemid/37b73d2a6c154bb4ab993d0fb463219c``
 - ``http://localhost:8080/ns1/@itemid/37b73d2a6c154bb4ab993d0fb463219c``
