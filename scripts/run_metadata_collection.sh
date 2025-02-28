#!/bin/bash
# Script to run metadata collection and storage

set -e  # Exit on error

echo "Running metadata collection and storage..."

# Check if the database template changes have been applied
if [ ! -f "news_storage/src/database.py.bak" ]; then
    echo "Applying database template changes first..."
    ./news_storage/scripts/apply_template_changes.sh
    
    echo "Applying database migrations..."
    alembic upgrade head
fi

# Run the metadata collection script
echo "Collecting and storing metadata..."
python scripts/collect_and_store_metadata.py

echo "Metadata collection and storage completed!"
