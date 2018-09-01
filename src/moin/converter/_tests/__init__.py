from moin.util.StringIOClosing import StringIO


def serialize(elem, **options):
    with StringIO() as buffer:
        elem.write(buffer.write, **options)
        return buffer.getvalue()