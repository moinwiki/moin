#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [ -f .env ]; then
    export $(cat .env | xargs)
fi

if [ -d .venv ]; then
    source .venv/bin/activate
fi

NAME=moin2
NUM_WORKERS=4
PIDFILE=moin2.pid
TIMEOUT=60

exec gunicorn 'moin.app:create_app()' \
--name $NAME \
--workers $NUM_WORKERS \
--timeout $TIMEOUT \
--log-level=debug \
--bind=127.0.0.1:5000 \
--pid=$PIDFILE
