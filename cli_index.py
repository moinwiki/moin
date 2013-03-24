# Copyright: 2013 MoinMoin:TarashishMishra
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
MoinMoin - Provide a web interface for index operations

"""


from moin import add_support_to_path
add_support_to_path()

from flask import render_template, request, redirect
from flask.ext.script import Manager

# Create the WSGI application object.
from MoinMoin.app import create_app
app = create_app()


@app.route('/+cli/index', methods=['POST', 'GET'])
def admin():
    if request.method == 'POST':
        command_list = request.form['command'].split()
        from MoinMoin.script import add_index_commands
        manager = Manager(create_app)
        add_index_commands(manager)
        try:
            manager.handle('moin', command_list[1], command_list[2:])
        except SystemExit:
            return "Invalid Command"
        return redirect('/')
    return render_template('cli_index.html')
