#!/bin/bash
set -e

. /venv/bin/activate

export PYTHONPATH=".:$PYTHONPATH"

exec "$@"
