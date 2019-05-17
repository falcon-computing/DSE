#!/bin/bash
. /opt/merlin/test/setup.sh
redis-server &> /dev/null &

exec "$@"
