#!/bin/bash

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p tmp
mkdir -p logs

# Set permissions
chmod 755 passenger_wsgi.py
chmod -R 755 venv
chmod -R 755 src
chmod -R 755 static
chmod -R 755 tmp
chmod -R 755 logs

# Create production .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    # Set production environment
    echo "ENV=production" >> .env
fi

# Create and populate the database
python populate_db.py

# Set appropriate permissions for the database
chmod 664 ~/checklist.db

echo "Setup complete! The application is ready to run." 