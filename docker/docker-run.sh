#!/bin/bash

docker run -it \
    -v "/curr/software":"/curr/software" \
    -v "$PWD":"/local" \
    -w="/local" \
    -u "$(id -u ${USER}):$(id -g ${USER})" \
    merlin-dse:latest \
    $@

