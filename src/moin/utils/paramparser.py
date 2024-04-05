# Copyright: 2010 MoinMoin:ThomasWaldmann
# Copyright: 2024 MoinMoin:UlrichB
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - parameter parsing and invoking of extension functions
"""

from functools import cmp_to_key

from moin.i18n import _


class BracketError(Exception):
    pass


class BracketUnexpectedCloseError(BracketError):
    def __init__(self, bracket):
        self.bracket = bracket
        BracketError.__init__(self, f"Unexpected closing bracket {bracket}")


class BracketMissingCloseError(BracketError):
    def __init__(self, bracket):
        self.bracket = bracket
        BracketError.__init__(self, f"Missing closing bracket {bracket}")


class ParserPrefix:
    """
    Trivial container-class holding a single character for
    the possible prefixes for parse_quoted_separated_ext
    and implementing rich equal comparison.
    """

    def __init__(self, prefix):
        self.prefix = prefix

    def __eq__(self, other):
        return isinstance(other, ParserPrefix) and other.prefix == self.prefix

    def __repr__(self):
        return "<ParserPrefix({})>".format(self.prefix.encode("utf-8"))


def parse_quoted_separated_ext(
    args,
    separator=None,
    name_value_separator=None,
    brackets=None,
    seplimit=0,
    multikey=False,
    prefixes=None,
    quotes="\"'",
):
    """
    Parses the given string according to the other parameters.

    Items can be quoted with any character from the quotes parameter
    and each quote can be escaped by doubling it, the separator and
    name_value_separator can both be quoted, when name_value_separator
    is set then the name can also be quoted.

    Values that are not given are returned as None, while the
    empty string as a value can be achieved by quoting it.

    If a name or value does not start with a quote, then the quote
    looses its special meaning for that name or value, unless it
    starts with one of the given prefixes (the parameter is a str
    containing all allowed prefixes.) The prefixes will be returned
    as ParserPrefix() instances in the first element of the tuple
    for that particular argument.

    If multiple separators follow each other, this is treated as
    having None arguments inbetween, that is also true for when
    space is used as separators (when separator is None), filter
    them out afterwards.

    The function can also do bracketing, i.e. parse expressions
    that contain things like::

        "(a (a b))" to ['(', 'a', ['(', 'a', 'b']],

    in this case, as in this example, the returned list will
    contain sub-lists and the brackets parameter must be a list
    of opening and closing brackets, e.g.::

        brackets = ['()', '<>']

    Each sub-list's first item is the opening bracket used for
    grouping.
    Nesting will be observed between the different types of
    brackets given. If bracketing doesn't match, a BracketError
    instance is raised with a 'bracket' property indicating the
    type of missing or unexpected bracket, the instance will be
    either of the class BracketMissingCloseError or of the class
    BracketUnexpectedCloseError.

    If multikey is True (along with setting name_value_separator),
    then the returned tuples for (key, value) pairs can also have
    multiple keys, e.g.::

        "a=b=c" -> ('a', 'b', 'c')

    :param args: arguments to parse
    :param separator: the argument separator, defaults to None, meaning any
        space separates arguments
    :param name_value_separator: separator for name=value, default '=',
        name=value keywords not parsed if evaluates to False
    :param brackets: a list of two-character strings giving
        opening and closing brackets
    :param seplimit: limits the number of parsed arguments
    :param multikey: multiple keys allowed for a single value
    :rtype: list
    :returns: list of strs and tuples containing strs,
              or lists containing the same for bracketing support
    """
    idx = 0
    assert name_value_separator is None or name_value_separator != separator
    assert name_value_separator is None or len(name_value_separator) == 1
    if not isinstance(args, str):
        raise TypeError("args must be str")
    max = len(args)
    result = []  # result list
    cur = [None]  # current item
    quoted = None  # we're inside quotes, indicates quote character used
    skipquote = 0  # next quote is a quoted quote
    noquote = False  # no quotes expected because word didn't start with one
    seplimit_reached = False  # number of separators exhausted
    separator_count = 0  # number of separators encountered
    SPACE = [" ", "\t"]
    nextitemsep = [separator]  # used for skipping trailing space
    SPACE = [" ", "\t"]
    if separator is None:
        nextitemsep = SPACE[:]
        separators = SPACE
    else:
        nextitemsep = [separator]  # used for skipping trailing space
        separators = [separator]
    if name_value_separator:
        nextitemsep.append(name_value_separator)

    # bracketing support
    opening = []
    closing = []
    bracketstack = []
    matchingbracket = {}
    if brackets:
        for o, c in brackets:
            assert o not in opening
            opening.append(o)
            assert c not in closing
            closing.append(c)
            matchingbracket[o] = c

    def additem(result, cur, separator_count, nextitemsep):
        if len(cur) == 1:
            result.extend(cur)
        elif cur:
            result.append(tuple(cur))
        cur = [None]
        noquote = False
        separator_count += 1
        seplimit_reached = False
        if seplimit and separator_count >= seplimit:
            seplimit_reached = True
            nextitemsep = [n for n in nextitemsep if n in separators]

        return cur, noquote, separator_count, seplimit_reached, nextitemsep

    while idx < max:
        char = args[idx]
        next = None
        if idx + 1 < max:
            next = args[idx + 1]
        if skipquote:
            skipquote -= 1
        if separator is not None and not quoted and char in SPACE:
            spaces = ""
            # accumulate all space
            while char in SPACE and idx < max - 1:
                spaces += char
                idx += 1
                char = args[idx]
            # remove space if args end with it
            if char in SPACE and idx == max - 1:
                break
            # remove space at end of argument
            if char in nextitemsep:
                continue
            idx -= 1
            if len(cur) and cur[-1]:
                cur[-1] += spaces
        elif not quoted and char == name_value_separator:
            if multikey or len(cur) == 1:
                cur.append(None)
            else:
                if not multikey:
                    if cur[-1] is None:
                        cur[-1] = ""
                    cur[-1] += name_value_separator
                else:
                    cur.append(None)
            noquote = False
        elif not quoted and not seplimit_reached and char in separators:
            (cur, noquote, separator_count, seplimit_reached, nextitemsep) = additem(
                result, cur, separator_count, nextitemsep
            )
        elif not quoted and not noquote and char in quotes:
            if len(cur) and cur[-1] is None:
                del cur[-1]
            cur.append("")
            quoted = char
        elif char == quoted and not skipquote:
            if next == quoted:
                skipquote = 2  # will be decremented right away
            else:
                quoted = None
        elif not quoted and char in opening:
            while len(cur) and cur[-1] is None:
                del cur[-1]
            (cur, noquote, separator_count, seplimit_reached, nextitemsep) = additem(
                result, cur, separator_count, nextitemsep
            )
            bracketstack.append((matchingbracket[char], result))
            result = [char]
        elif not quoted and char in closing:
            while len(cur) and cur[-1] is None:
                del cur[-1]
            (cur, noquote, separator_count, seplimit_reached, nextitemsep) = additem(
                result, cur, separator_count, nextitemsep
            )
            cur = []
            if not bracketstack:
                raise BracketUnexpectedCloseError(char)
            expected, oldresult = bracketstack[-1]
            if expected != char:
                raise BracketUnexpectedCloseError(char)
            del bracketstack[-1]
            oldresult.append(result)
            result = oldresult
        elif not quoted and prefixes and char in prefixes and cur == [None]:
            cur = [ParserPrefix(char)]
            cur.append(None)
        else:
            if len(cur):
                if cur[-1] is None:
                    cur[-1] = char
                else:
                    cur[-1] += char
            else:
                cur.append(char)
            noquote = True

        idx += 1

    if bracketstack:
        raise BracketMissingCloseError(bracketstack[-1][0])

    if quoted:
        if len(cur):
            if cur[-1] is None:
                cur[-1] = quoted
            else:
                cur[-1] = quoted + cur[-1]
        else:
            cur.append(quoted)

    additem(result, cur, separator_count, nextitemsep)

    return result


def parse_quoted_separated(args, separator=",", name_value=True, seplimit=0):
    result = []
    positional = result
    if name_value:
        name_value_separator = "="
        trailing = []
        keywords = {}
    else:
        name_value_separator = None

    items = parse_quoted_separated_ext(
        args, separator=separator, name_value_separator=name_value_separator, seplimit=seplimit
    )
    for item in items:
        if isinstance(item, tuple):
            key, value = item
            if key is None:
                key = ""
            keywords[key] = value
            positional = trailing
        else:
            positional.append(item)

    if name_value:
        return result, keywords, trailing
    return result


def get_bool(arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a boolean from a str.
    Valid input is 'true'/'false', 'yes'/'no' and '1'/'0' or None for
    the default value.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param default: default value if arg is None
    :rtype: boolean or None
    :returns: the boolean value of the string according to above rules
              (or default value)
    """
    assert default is None or isinstance(default, bool)
    if arg is None:
        return default
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")
    arg = arg.lower()
    if arg in ["0", "false", "no"]:
        return False
    elif arg in ["1", "true", "yes"]:
        return True
    else:
        if name:
            raise ValueError(_('Argument "{name}" must be a boolean value, not "{value}"').format(name=name, value=arg))
        else:
            raise ValueError(_('Argument must be a boolean value, not "{value}"').format(value=arg))


def get_int(arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return an integer from a str
    containing the decimal representation of a number.
    None is a valid input and yields the default value.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param default: default value if arg is None
    :rtype: int or None
    :returns: the integer value of the string (or default value)
    """
    assert default is None or isinstance(default, int)
    if arg is None:
        return default
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")
    try:
        return int(arg)
    except ValueError:
        if name:
            raise ValueError(
                _('Argument "{name}" must be an integer value, not "{value}"').format(name=name, value=arg)
            )
        else:
            raise ValueError(_('Argument must be an integer value, not "{value}"').format(value=arg))


def get_float(arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a float from a str.
    None is a valid input and yields the default value.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param default: default return value if arg is None
    :rtype: float or None
    :returns: the float value of the string (or default value)
    """
    assert default is None or isinstance(default, (int, float))
    if arg is None:
        return default
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")
    try:
        return float(arg)
    except ValueError:
        if name:
            raise ValueError(
                _('Argument "{name}" must be a floating point value, not "{value}"').format(name=name, value=arg)
            )
        else:
            raise ValueError(_('Argument must be a floating point value, not "{value}"').format(value=arg))


def get_complex(arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a complex from a str.
    None is a valid input and yields the default value.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param default: default return value if arg is None
    :rtype: complex or None
    :returns: the complex value of the string (or default value)
    """
    assert default is None or isinstance(default, (int, float, complex))
    if arg is None:
        return default
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")
    try:
        # allow writing 'i' instead of 'j'
        arg = arg.replace("i", "j").replace("I", "j")
        return complex(arg)
    except ValueError:
        if name:
            raise ValueError(_('Argument "{name}" must be a complex value, not "{value}"').format(name=name, value=arg))
        else:
            raise ValueError(_('Argument must be a complex value, not "{value}"').format(value=arg))


def get_str(arg, name=None, default=None):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a str.
    None is a valid input and yields the default value.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param default: default return value if arg is None;
    :rtype: str or None
    :returns: the str (or default value)
    """
    assert default is None or isinstance(default, str)
    if arg is None:
        return default
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")

    return arg


def get_choice(arg, name=None, choices=[None], default_none=False):
    """
    For use with values returned from parse_quoted_separated or given
    as macro parameters, return a str that must be in the
    choices given. None is a valid input and yields first of the valid
    choices.

    :param arg: The argument, may be None or a str
    :param name: Name of the argument, for error messages
    :param choices: the possible choices
    :param default_none: If False (default), get_choice returns first available
                         choice if arg is None. If True, get_choice returns
                         None if arg is None. This is useful if some arg value
                         is required (no default choice).
    :rtype: str or None
    :returns: the str (or default value)
    """
    assert isinstance(choices, (tuple, list))
    if arg is None:
        if default_none:
            return None
        else:
            return choices[0]
    elif not isinstance(arg, str):
        raise TypeError("Argument must be None or str")
    elif arg not in choices:
        if name:
            raise ValueError(
                _(
                    'Argument "{name}" must be one of "{choices}").format(not "{value}"',
                    name=name,
                    choices='", "'.join([repr(choice) for choice in choices]),
                    value=arg,
                )
            )
        else:
            raise ValueError(
                _(
                    'Argument must be one of "{choices}").format(not "{value}"',
                    choices='", "'.join([repr(choice) for choice in choices]),
                    value=arg,
                )
            )

    return arg


class IEFArgument:
    """
    Base class for new argument parsers for
    invoke_extension_function.
    """

    def __init__(self):
        pass

    def parse_argument(self, s):
        """
        Parse the argument given in s (a string) and return
        the argument for the extension function.
        """
        raise NotImplementedError

    def get_default(self):
        """
        Return the default for this argument.
        """
        raise NotImplementedError


class UnitArgument(IEFArgument):
    """
    Argument class for invoke_extension_function that forces
    having any of the specified units given for a value.

    Note that the default unit is "mm".

    Use, for example, "UnitArgument('7mm', float, ['%', 'mm'])".

    If the defaultunit parameter is given, any argument that
    can be converted into the given argtype is assumed to have
    the default unit. NOTE: This doesn't work with a choice
    (tuple or list) argtype.
    """

    def __init__(self, default, argtype, units=["mm"], defaultunit=None):
        """
        Initialise a UnitArgument giving the default,
        argument type and the permitted units.
        """
        IEFArgument.__init__(self)
        self._units = list(units)
        self._units.sort(key=cmp_to_key(lambda x, y: len(y) - len(x)))
        self._type = argtype
        self._defaultunit = defaultunit
        assert defaultunit is None or defaultunit in units
        if default is not None:
            self._default = self.parse_argument(default)
        else:
            self._default = None

    def parse_argument(self, s):
        for unit in self._units:
            if s.endswith(unit):
                ret = (self._type(s[: len(s) - len(unit)]), unit)
                return ret
        if self._defaultunit is not None:
            try:
                return self._type(s), self._defaultunit
            except ValueError:
                pass
        units = ", ".join(self._units)
        # XXX: how can we translate this?
        raise ValueError(f"Invalid unit in value {s} (allowed units: {units})")

    def get_default(self):
        return self._default


class required_arg:
    """
    Wrap a type in this class and give it as default argument
    for a function passed to invoke_extension_function() in
    order to get generic checking that the argument is given.
    """

    def __init__(self, argtype):
        """
        Initialise a required_arg
        :param argtype: the type the argument should have
        """
        if not (argtype in (bool, int, float, complex, str) or isinstance(argtype, (IEFArgument, tuple, list))):
            raise TypeError("argtype must be a valid type")
        self.argtype = argtype


def invoke_extension_function(function, args, fixed_args=[]):
    """
    Parses arguments for an extension call and calls the extension
    function with the arguments.

    If the macro function has a default value that is a bool,
    int, float or str object, then the given value
    is converted to the type of that default value before passing
    it to the macro function. That way, macros need not call the
    get_* functions for any arguments that have a default.

    :param function: the function to invoke
    :param args: str with arguments (or evaluating to False)
    :param fixed_args: fixed arguments to pass as the first arguments
    :returns: the return value from the function called
    """
    from inspect import getfullargspec, isfunction, isclass, ismethod

    def _convert_arg(value, default, name=None):
        """
        Using the get_* functions, convert argument to the type of the default
        if that is any of bool, int, float or str; if the default
        is the type itself then convert to that type (keeps None) or if the
        default is a list require one of the list items.

        In other cases return the value itself.
        """
        # if extending this, extend required_arg as well!
        if isinstance(default, bool):
            return get_bool(value, name, default)
        elif isinstance(default, int):
            return get_int(value, name, default)
        elif isinstance(default, float):
            return get_float(value, name, default)
        elif isinstance(default, complex):
            return get_complex(value, name, default)
        elif isinstance(default, str):
            return get_str(value, name, default)
        elif isinstance(default, (tuple, list)):
            return get_choice(value, name, default)
        elif default is bool:
            return get_bool(value, name)
        elif default is int:
            return get_int(value, name)
        elif default is float:
            return get_float(value, name)
        elif default is complex:
            return get_complex(value, name)
        elif isinstance(default, IEFArgument):
            # defaults handled later
            if value is None:
                return None
            return default.parse_argument(value)
        elif isinstance(default, required_arg):
            if isinstance(default.argtype, (tuple, list)):
                # treat choice specially and return None if no choice
                # is given in the value
                return get_choice(value, name, list(default.argtype), default_none=True)
            else:
                return _convert_arg(value, default.argtype, name)
        return value

    assert isinstance(fixed_args, (list, tuple))

    kwargs = {}
    kwargs_to_pass = {}
    trailing_args = []

    if args:
        assert isinstance(args, str)

        positional, keyword, trailing = parse_quoted_separated(args)

        for kw in keyword:
            kwargs[kw] = keyword[kw]

        trailing_args.extend(trailing)

    else:
        positional = []

    if isfunction(function) or ismethod(function):
        f = function
    elif isclass(function):
        f = function.__init__
    else:
        raise TypeError("function must be a function, method or class")
    argnames, varargs, varkw, defaultlist, kwonlyargs, kwonlydefaults, annotations = getfullargspec(f)

    # self is implicit!
    if ismethod(function) or isclass(function):
        argnames = argnames[1:]

    fixed_argc = len(fixed_args)
    argnames = argnames[fixed_argc:]
    argc = len(argnames)
    if not defaultlist:
        defaultlist = []

    # if the fixed parameters have defaults too...
    if argc < len(defaultlist):
        defaultlist = defaultlist[fixed_argc:]
    defstart = argc - len(defaultlist)

    defaults = {}
    # reverse to be able to pop() things off
    positional.reverse()
    allow_kwargs = False
    allow_trailing = False
    # convert all arguments to keyword arguments,
    # fill all arguments that weren't given with None
    for idx in range(argc):
        argname = argnames[idx]
        if argname == "_kwargs":
            allow_kwargs = True
            continue
        if argname == "_trailing_args":
            allow_trailing = True
            continue
        if positional:
            kwargs[argname] = positional.pop()
        if argname not in kwargs:
            kwargs[argname] = None
        if idx >= defstart:
            defaults[argname] = defaultlist[idx - defstart]

    if positional:
        if not allow_trailing:
            raise ValueError(_("Too many arguments"))
        trailing_args.extend(positional)

    if trailing_args:
        if not allow_trailing:
            raise ValueError(_("Cannot have arguments without name following" " named arguments"))
        kwargs["_trailing_args"] = trailing_args

    # type-convert all keyword arguments to the type
    # that the default value indicates
    for argname in list(kwargs.keys()):  # new list object with keys for iteration as we modify kwargs
        if argname in defaults:
            # the value of 'argname' from kwargs will be put into the
            # macro's 'argname' argument, so convert that giving the
            # name to the converter so the user is told which argument
            # went wrong (if it does)
            kwargs[argname] = _convert_arg(kwargs[argname], defaults[argname], argname)
            if kwargs[argname] is None:
                if isinstance(defaults[argname], required_arg):
                    raise ValueError(_('Argument "{name}" is required').format(name=argname))
                if isinstance(defaults[argname], IEFArgument):
                    kwargs[argname] = defaults[argname].get_default()

        if argname not in argnames:
            # move argname into _kwargs parameter
            kwargs_to_pass[argname] = kwargs[argname]
            del kwargs[argname]

    if kwargs_to_pass:
        kwargs["_kwargs"] = kwargs_to_pass
        if not allow_kwargs:
            raise ValueError(_('No argument named "{name}"').format(name=list(kwargs_to_pass.keys())[0]))

    return function(*fixed_args, **kwargs)
