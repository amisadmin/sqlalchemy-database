#!/bin/sh -e

export PREFIX=""
if [ -d 'venv' ] ; then
    export PREFIX="venv/bin/"
fi

set -x
${PREFIX}coverage run -m pytest
${PREFIX}coverage report --show-missing --skip-covered --fail-under=100