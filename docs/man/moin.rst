:orphan:

Moin Command Line Interface
===========================

:program:`moin` is the command line interface to miscellaneous MoinMoin Wiki related
tools.

If you invoke :program:`moin` without any arguments, it will show a short quick help,

`moin --help` will show a more complete overview:

::

    Usage: moin [OPTIONS] COMMAND [ARGS]...

      Moin extensions to the Flask CLI

    Options:
      -e, --env-file FILE   Load environment variables from this file. python-
                            dotenv must be installed.
      -A, --app IMPORT      The Flask application or factory function to load, in
                            the form 'module:name'. Module can be a dotted import
                            or file path. Name is not required if it is 'app',
                            'application', 'create_app', or 'make_app', and can be
                            'name(args)' to pass arguments.
      --debug / --no-debug  Set debug mode.
      --version             Show the Flask version.
      --help                Show this message and exit.

    Commands:
      account-create           Create a user account
      account-disable          Disable user accounts
      account-password         Set user passwords
      create-instance          Create wikiconfig and wiki instance...
      dump-help                Dump a namespace of user help items to .data...
      dump-html                Create a static HTML image of this wiki
      help                     Quick help
      import19                 Import content and user data from a moin 1.9 wiki
      index-build              Build the indexes
      index-create             Create empty indexes
      index-destroy            Destroy the indexes
      index-dump               Dump the indexes in readable form to stdout
      index-move               Move the indexes from the temporary to the...
      index-optimize           Optimize the indexes
      index-update             Update the indexes
      item-get                 Get an item revision from the wiki
      item-put                 Put an item revision into the wiki
      load                     Deserialize a file into the backend; with...
      load-help                Load a directory of help .data and .meta file...
      maint-reduce-revisions   Remove all revisions but the last one from all...
      maint-set-meta           Set meta data of a new revision
      maint-validate-metadata  Find and optionally fix issues with item metadata
      routes                   Show the routes for the app.
      run                      Run a development server.
      save                     Serialize the backend into a file
      shell                    Run a shell in the app context.
      welcome                  Load initial welcome page into an empty wiki



See also
--------

:manpage:`moinmoin(1)`
