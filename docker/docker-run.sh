#!/bin/bash
script_dir=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)
#cmd=$(echo $(readlink -f $1))

#shift
docker run -it \
    -v "$script_dir/..":"/opt/merlin_dse" \
    -v "$MERLIN_COMPILER_HOME":"/opt/merlin" \
    -v "/curr/software":"/curr/software" \
    -v "$PWD":"/local" \
    -w="/local" \
    -u "$(id -u ${USER}):$(id -g ${USER})" \
    merlin-dse:latest \
    $@

