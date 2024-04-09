# Copyright: 2009 MoinMoin:BastianBlank
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - MIME helpers
"""


from collections import namedtuple
from moin.utils.pysupport import AutoNe


class Type(namedtuple("Type", "type subtype parameters"), AutoNe):
    """
    :ivar type: Type part
    :type type: str
    :ivar subtype: Subtype part
    :type subtype: str
    :ivar parameters: Parameters part
    :type parameters: dict
    """

    __token_allowed = s = frozenset(
        r"""!#$%&'*+-.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ""" r"""^_`abcdefghijklmnopqrstuvwxyz{|}~"""
    )

    def __new__(cls, _type=None, type=None, subtype=None, parameters=None):
        """
        :param _type: Type object or string representation
        :keyword type: Type part
        :keyword subtype: Subtype part
        :keyword parameters: Parameters part
        """
        if isinstance(_type, Type):
            new_type, new_subtype, new_parameters = _type.type, _type.subtype, _type.parameters.copy()
        elif _type:
            new_type, new_subtype, new_parameters = cls._parse(_type)
        else:
            new_type = new_subtype = None
            new_parameters = {}

        if type is not None:
            new_type = type
        if subtype is not None:
            new_subtype = subtype
        if parameters is not None:
            new_parameters.update(parameters)

        return super().__new__(cls, new_type, new_subtype, new_parameters)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(self.__class__(other))

        if isinstance(other, Type):
            return super().__eq__(other)

        return NotImplemented

    def __str__(self):
        ret = ["{}/{}".format(self.type or "*", self.subtype or "*")]

        parameters = sorted(self.parameters.items())
        for key, value in parameters:
            if self.__token_check(value):
                ret.append(f"{key}={value}")
            else:
                ret.append(f'{key}="{value}"')

        return ";".join(ret)

    def __token_check(self, value):
        token_allowed = self.__token_allowed
        for v in value:
            if v not in token_allowed:
                return False
        return True

    @classmethod
    def _parse(cls, type):
        parts = type.split(";")

        type, subtype = parts[0].strip().lower().split("/", 1)

        type = type != "*" and type or ""
        subtype = subtype != "*" and subtype or ""
        parameters = {}

        for param in parts[1:]:
            key, value = param.strip().split("=", 1)
            # remove quotes
            if value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            parameters[key.lower()] = value

        return type, subtype, parameters

    def issupertype(self, other):
        """
        Check if this object is a super type of the other

        A super type is defined as
        - the other type matches this (possibly wildcard) type,
        - the other subtype matches this (possibly wildcard) subtype and
        - the other parameters are a supperset of this one.
        """
        if isinstance(other, Type):
            if self.type and self.type != other.type:
                return False
            if self.subtype and self.subtype != other.subtype:
                return False
            self_params = set(self.parameters.items())
            other_params = set(other.parameters.items())
            return self_params <= other_params

        raise ValueError


# Own types, application type
type_moin_document = Type(type="application", subtype="x.moin.document")

# Own types, text type
type_moin_creole = Type(type="text", subtype="x.moin.creole")
type_moin_wiki = Type(type="text", subtype="x.moin.wiki")

# Generic types, text type
type_text_plain = Type(type="text", subtype="plain")
