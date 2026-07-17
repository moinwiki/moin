#!/usr/bin/env bash

set -o errexit
set -o pipefail

command=
wheel=
tag_name=moin2

if [ -f .env ]
then
    echo "reading content of .env"
    export $(cat .env | xargs)
fi

usage() {
    echo "usage: $0 [--docker] [--podman] [--wheel <path>]"
}

find_wheel() {
    wheel_path=$(find ./dist -type f -name '*.whl' -exec ls -t1 {} + | head -1)
    wheel=$(basename "$wheel_path")
    if test "$wheel" == ""
    then
        echo "no wheel file found for moin2 in subfolder ./dist"
        exit 1
    fi
    echo "wheel file: $wheel"
}

while [ $# -ne 0 ]
do
    case "$1" in
      --docker)
        command=docker
        ;;
      --podman)
        command=podman
        ;;
      --wheel)
        shift
        wheel=$1
        ;;
      *)
        usage
        exit 1
    esac
    shift
done

if [ -z "$command" ]
then
    command=$CONTAINER_RUNTIME
    if [ -z "$command" ]
    then
        usage
        exit 1
    fi
fi

if [ -z "$wheel" ]
then
    find_wheel
    if [ -z "$wheel" ]
    then
        usage
    fi
fi

if [ ! -r "dist/$wheel" ]
then
    echo "wheel file not found: $wheel"
    exit 1
fi

$command image build -f contrib/docker/Dockerfile --tag $tag_name --build-arg wheel=$wheel .
