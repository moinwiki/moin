# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - creates an item

    This script creates a new revision of an item.
"""


from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin.storage.error import ItemAlreadyExistsError, NoSuchItemError


class Create_Item(Command):
    description = 'This command can be used to create an item'
    option_list = (
        Option('--name', '-n', dest='name', type=unicode, required=True,
            help='Name of the item to create'),
        Option('--file', '-f', dest='data_file', type=unicode, required=True,
            help='Filename of file to read in and store as item.'),
        Option('--mimetype', '-m', dest='mimetype', type=unicode, required=True,
            help='mimetype of item'),
        Option('--comment', '-c', dest='comment', type=unicode,
            help='comment for item')
    )

    def run(self, name, data_file, mimetype, comment):
        storage = app.unprotected_storage
        rev_no = -1
        try:
            item = storage.create_item(name)
        except ItemAlreadyExistsError:
            item = storage.get_item(name)
            currentrev = item.get_revision(-1)
            rev_no = currentrev.revno
        rev = item.create_revision(rev_no + 1)
        rev['action'] = u'SAVE'
        rev['name'] = name
        rev['mimetype'] = mimetype
        data = open(data_file, 'rb')
        rev.write(data.read())
        item.commit()
        data.close()
