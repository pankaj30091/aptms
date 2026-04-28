#!/bin/bash
set -e
cd "$(dirname "$0")"

source /home/psharma/envs/base/bin/activate

# Run migrations and seed on first run
FLASK_APP=wsgi:app flask db upgrade
python seed.py

# Start dev server
FLASK_APP=wsgi:app flask run --host=0.0.0.0 --port=8200
