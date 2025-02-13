#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to activate virtual environment
activate_venv() {
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "Creating virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
    fi
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "Installing package in development mode..."
    pip install -e .
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
}

# Function to start the development server
run_dev() {
    echo "Starting development server..."
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
}

# Function to start the production server
run_prod() {
    echo "Starting production server..."
    gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}
}

# Function to run tests
run_tests() {
    echo "Running tests..."
    pytest
}

# Main script
case "$1" in
    "dev")
        activate_venv
        run_migrations
        run_dev
        ;;
    "prod")
        activate_venv
        run_migrations
        run_prod
        ;;
    "test")
        activate_venv
        run_tests
        ;;
    "migrate")
        activate_venv
        run_migrations
        ;;
    *)
        echo "Usage: ./run.sh [dev|prod|test|migrate]"
        echo "  dev     - Run in development mode with auto-reload"
        echo "  prod    - Run in production mode with gunicorn"
        echo "  test    - Run tests"
        echo "  migrate - Run database migrations"
        exit 1
        ;;
esac 