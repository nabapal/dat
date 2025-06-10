#!/bin/bash
# Run the Flask Daily Activity Tracker app

source venv/bin/activate
export FLASK_APP=app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5004
