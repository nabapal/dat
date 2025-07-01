#!/bin/bash
# Only start the Flask app, do NOT reseed the database every time

set -e

# Activate virtual environment
source venv/bin/activate

# Start the Flask app on port 5004
python3 run.py --port=5004
