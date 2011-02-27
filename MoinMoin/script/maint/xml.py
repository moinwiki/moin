"""
    MoinMoin - XML (un)serialization of storage contents.

    Using --save you can serialize your storage contents to an xml file.
    Using --load you can load such a file into your storage.

    Note that before unserializing stuff, you should first create an
    appropriate namespace_mapping in your wiki configuration so that the
    items get written to the backend where you want them.

    @copyright: 2009 MoinMoin:ChristopherDenter,
                2009 MoinMoin:ThomasWaldmann
    @license: GNU GPL v2 (or any later version), see LICENSE.txt for details.
"""

import sys, time

from flask import flaskg

from MoinMoin.script import MoinScript, fatal
from MoinMoin.wsgiapp import init_unprotected_backends

from MoinMoin.storage.serialization import unserialize, serialize, \
                                           NLastRevs, SinceTime


class PluginScript(MoinScript):
    """XML Load/Save Script"""
    def __init__(self, argv, def_values):
        MoinScript.__init__(self, argv, def_values)
        self.parser.add_option(
            "-s", "--save", dest="save", action="store_true",
            help="Save (serialize) storage contents to a xml file."
        )
        self.parser.add_option(
            "-l", "--load", dest="load", action="store_true",
            help="Load (unserialize) storage contents from a xml file."
        )
        self.parser.add_option(
            "-f", "--file", dest="xml_file", action="store", type="string",
            help="Filename of xml file to use [Default: use stdin/stdout]."
        )
        self.parser.add_option(
            "--nrevs", dest="nrevs", action="store", type="int", default=0,
            help="Serialize only the last n revisions of each item [Default: all everything]."
        )
        self.parser.add_option(
            "--exceptnrevs", dest="exceptnrevs", action="store", type="int", default=0,
            help="Serialize everything except the last n revisions of each item [Default: everything]."
        )
        self.parser.add_option(
            "--ndays", dest="ndays", action="store", type="int", default=0,
            help="Serialize only the last n days of each item [Default: everything]."
        )
        self.parser.add_option(
            "--exceptndays", dest="exceptndays", action="store", type="int", default=0,
            help="Serialize everything except the last n days of each item [Default: everything]."
        )
        self.parser.add_option(
            "--nhours", dest="nhours", action="store", type="int", default=0,
            help="Serialize only the last n hours of each item [Default: everything]."
        )
        self.parser.add_option(
            "--exceptnhours", dest="exceptnhours", action="store", type="int", default=0,
            help="Serialize everything except the last n hours of each item [Default: everything]."
        )

    def mainloop(self):
        load = self.options.load
        save = self.options.save
        xml_file = self.options.xml_file

        if load == save: # either both True or both False
            fatal("You need to give either --load or --save!")
        if not xml_file:
            if load:
                xml_file = sys.stdin
            elif save:
                xml_file = sys.stdout

        self.init_request()
        request = self.request
        init_unprotected_backends(request)
        storage = flaskg.unprotected_storage

        ndays = self.options.ndays
        exceptndays = self.options.exceptndays
        nhours = self.options.nhours
        exceptnhours = self.options.exceptnhours
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

        nrevs = self.options.nrevs
        nrevs_invert = False
        exceptnrevs = self.options.exceptnrevs
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

