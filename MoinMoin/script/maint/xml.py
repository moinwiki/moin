# Copyright: 2009 MoinMoin:ChristopherDenter
# Copyright: 2009 MoinMoin:ThomasWaldmann
# Copyright: 2011 MoinMoin:ReimarBauer
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
    MoinMoin - XML (un)serialization of storage contents.

    Using --save you can serialize your storage contents to an xml file.
    Using --load you can load such a file into your storage.

    Note that before unserializing stuff, you should first create an
    appropriate namespace_mapping in your wiki configuration so that the
    items get written to the backend where you want them.
"""


import sys, time

from flask import flaskg
from flask import current_app as app
from flaskext.script import Command, Option

from MoinMoin.script import fatal

from MoinMoin.storage.serialization import unserialize, serialize, \
                                           NLastRevs, SinceTime

class XML(Command):
    description = "This command can be used to save items to a file or to create items by loading from a file"
    option_list = (
        Option('--save', '-s', dest='save', action='store_true',
            help='Save (serialize) storage contents to a xml file.'),
        Option('--load', '-l', dest='load', action='store_true',
            help='Load (unserialize) storage contents from a xml file.'),
        Option('--file', '-f', dest='xml_file', type=unicode,
            help='Filename of xml file to use [Default: use stdin/stdout].'),
        Option('--nrevs', dest='nrevs', type=int, default=0,
            help='Serialize only the last n revisions of each item [Default: all everything].'),
        Option('--exceptnrevs', dest='exceptnrevs', type=int, default=0,
            help='Serialize everything except the last n revisions of each item [Default: everything].'),
        Option('--ndays', dest='ndays', type=int, default=0,
            help='Serialize only the last n days of each item [Default: everything].'),
        Option('--exceptndays', dest='exceptndays', type=int, default=0,
            help='Serialize everything except the last n days of each item [Default: everything].'),
        Option('--nhours', dest='nhours', type=int, default=0,
            help='Serialize only the last n hours of each item [Default: everything].'),
        Option('--exceptnhours', dest='exceptnhours', type=int, default=0,
            help='Serialize everything except the last n hours of each item [Default: everything].')
    )

    def run(self, save, load, xml_file, nrevs, exceptnrevs, ndays, exceptndays, nhours, exceptnhours):
        if load == save: # either both True or both False
            fatal("You need to give either --load or --save!")
        if not xml_file:
            if load:
                xml_file = sys.stdin
            elif save:
                xml_file = sys.stdout

        storage = app.unprotected_storage
        now = time.time()

        sincetime = 0
        sincetime_invert = False
        if ndays:
            sincetime = now - ndays * 24 * 3600
        elif nhours:
            sincetime = now - nhours * 3600
        elif exceptndays:
            sincetime = now - exceptndays * 24 * 3600
            sincetime_invert = True
        elif exceptnhours:
            sincetime = now - exceptnhours * 3600
            sincetime_invert = True

        nrevs_invert = False
        if exceptnrevs:
            nrevs = exceptnrevs
            nrevs_invert = True

        if load:
            unserialize(storage, xml_file)
        elif save:
            if nrevs:
                serialize(storage, xml_file, NLastRevs, nrevs, nrevs_invert)
            elif sincetime:
                serialize(storage, xml_file, SinceTime, sincetime, sincetime_invert)
            else:
                serialize(storage, xml_file)

