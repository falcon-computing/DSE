#!/bin/bash

if [ ! $MERLIN_COMPILER_HOME ]; then
    echo "MERLIN_COMPILER_HOME is not set!"
    exit 0
fi

script_dir=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)

docker run -it \
    -v "$script_dir/..":"/opt/merlin_dse" \
    -v "$MERLIN_COMPILER_HOME":"/opt/merlin" \
    -v "/curr/software":"/curr/software" \
    -v "$HOME":"/home" \
    -v "$PWD":"/local" \
    -w="/local" \
    -u "$(id -u ${USER}):$(id -g ${USER})" \
    merlin-dse:latest \
    $@

