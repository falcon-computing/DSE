#!/bin/bash
script_dir=$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)

function git_cmd() {
  cd $script_dir && git $@;
}
git_branch=$(git_cmd branch | grep \* | cut -d ' ' -f2 | tr -d '(')

docker_tag=latest
