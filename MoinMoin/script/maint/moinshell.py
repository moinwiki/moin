# -*- coding: utf-8 -*-

from flask import Flask, _request_ctx_stack
from flask import current_app as app
from flask import g as flaskg
from flaskext.script import Command, Option

from MoinMoin import user
from MoinMoin.util.clock import Clock

class MoinShell(Command):

    """
    Runs a Python shell inside Flask application context.

    :param banner: banner appearing at top of shell when started
    :param make_context: a callable returning a dict of variables 
                         used in the shell namespace. By default 
                         returns a dict consisting of just the app.
    :param use_ipython: use IPython shell if available, ignore if not. 
                        The IPython shell can be turned off in command 
                        line by passing the **--no-ipython** flag.
    """

    banner = ''

    description = 'Runs a Python shell inside Flask application context.'
    
    def __init__(self, banner=None, make_context=None, use_ipython=True):


        self.banner = banner or self.banner
        self.use_ipython = use_ipython

        if make_context is None:
            def make_context():
                app = _request_ctx_stack.top.app
                flaskg.unprotected_storage = app.storage
                flaskg.groups = app.cfg.groups()
                flaskg.storage = app.storage
                flaskg.user = user.User()
                flaskg.clock = Clock()
                return dict(app=app, flaskg=flaskg)

        self.make_context = make_context
    
    def get_options(self):

        return (
                Option('--no-ipython',
                       action="store_true",
                       dest='no_ipython',
                       default=not(self.use_ipython)),)

    def get_context(self):
        
        """
        Returns a dict of context variables added to the shell namespace.
        """

        return self.make_context()

    def run(self, no_ipython):

        """
        Runs the shell. Unless no_ipython is True or use_python is False
        then runs IPython shell if that is installed.
        """
        

        context = self.get_context()

        from IPython import embed

        embed()

