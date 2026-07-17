#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ -f .env ]; then
    export $(cat .env | xargs)
fi

if [ -d .venv ]; then
    source .venv/bin/activate
fi

exec hypercorn --config ${SCRIPT_DIR}/config-test.toml 'wsgi:moin.app:create_app()'
