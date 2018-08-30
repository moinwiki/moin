from StringIO import StringIO as StringIOBase


class StringIO(StringIOBase):
    """
    same as StringIO from stdlib, but enhanced with a context manager, so it
    can be used within a "with" statement and gets automatically closed when
    the with-block is left. The standard "file" object behaves that way, so
    a StringIO "file emulation" should behave the same.
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()
