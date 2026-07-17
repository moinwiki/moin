Install the [Hypercorn](https://github.com/pgjones/hypercorn) ASGI and WSGI server in your local Moin2 venv using

```
$ . active
(.venv) $ pip install -r contrib/hypercorn/requirements.txt
```

The Hypercorn version is pinned to 0.17.3 because of [known issues](https://github.com/pgjones/hypercorn/issues/331)
with the latest 0.18.0 release.

Use with VSCode: here is a launch configuration making use of Hypercorn to run Moin2

```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Launch WSGI server",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/.venv/bin/hypercorn",
            "args": [
                "--config",
                "${workspaceFolder}/contrib/hypercorn/config-test.toml",
                "wsgi:moin.app:create_app()"
            ],
            "jinja": true,
            "justMyCode": false,
            "cwd": "${workspaceFolder}",
            "env": {
                "FLASK_DEBUG": "0",
                "WERKZEUG_DEBUG_PIN": "off"
            }
        }
    ]
}
```
