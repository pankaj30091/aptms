#!/bin/bash
set -e
cd "$(dirname "$0")"

source /home/psharma/envs/aptms/bin/activate

# Run migrations and seed on first run
flask db upgrade
python seed.py

# Start dev server
python wsgi.py
