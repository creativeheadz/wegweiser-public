#!/bin/bash

# Script to run the tags table migration

echo "Running tags table migration..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
fi

# Run the migration script
python migrations/update_tags_unique_constraint.py

# Check if the migration was successful
if [ $? -eq 0 ]; then
    echo "Migration completed successfully!"
else
    echo "Migration failed. Please check the logs for details."
    exit 1
fi

echo "Done."
