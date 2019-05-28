# +++++++++++ CUSTOM WSGI +++++++++++
# If you have a WSGI file that you want to serve using PythonAnywhere, perhaps
# in your home directory under version control, then use something like this:
#
import sys

path = '/home/MoinMoin2/moin'
if path not in sys.path:
    sys.path.append(path)

from wsgi import application  # noqa
