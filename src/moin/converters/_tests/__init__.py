import re
from io import StringIO


def serialize(elem, **options):
    with StringIO() as buffer:
        elem.write(buffer.write, **options)
        return buffer.getvalue()


# use non-greedy match for "..." part!
XMLNS_RE = re.compile(r'\s+xmlns(:\S+)?="[^"]+?"')
XMLNS_RE2 = re.compile(r'(\s+xmlns(:\w+)?="[^"]+?"|xmlns\(\w+=[^)]+?\)\s+)')
XMLNS_RE3 = re.compile(r'\s+xmlns="[^"]+?"')

TAGSTART_RE = re.compile(r"^(<[a-z:]+)")
