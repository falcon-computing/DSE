#!/bin/bash

script_dir=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)

docker run -it \
    -v "$script_dir/..":"/opt/merlin_dse" \
    -v "/curr/software":"/curr/software" \
    -v "$HOME":"/home" \
    -v "$PWD":"/local" \
    -w="/local" \
    -u "$(id -u ${USER}):$(id -g ${USER})" \
    merlin-dse:latest \
    $@

