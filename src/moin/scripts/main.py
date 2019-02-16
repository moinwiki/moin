# Usually, installing moin via setup.py or with pip, setuptools creates
# platform specific adapters (like a "moin" script on linux or "moin.exe" /
# "moin-script.py" on windows), but they are usually somewhere in the install
# path, so it is easier to find if we have this in-tree.
#
# So, just use this to invoke with python:

if __name__ == '__main__':
    import sys
    from moin.scripts import main
    rc = main()
    sys.exit(rc)
