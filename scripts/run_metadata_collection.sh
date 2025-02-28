#!/bin/bash
# Script to run metadata collection and storage

set -e  # Exit on error

echo "Running metadata collection and storage..."

# Check if the database template changes have been applied
if [ ! -f "news_storage/src/database.py.bak" ]; then
    echo "Applying database template changes first..."
    
    # Make sure the script is executable
    chmod +x news_storage/scripts/apply_template_changes.sh
    
    # Run the script
    ./news_storage/scripts/apply_template_changes.sh || {
        echo "Error applying database template changes"
        exit 1
    }
    
    echo "Applying database migrations..."
    alembic upgrade head || {
        echo "Error applying database migrations"
        exit 1
    }
else
    echo "Database template changes already applied"
fi

# Run the metadata collection script
echo "Collecting and storing metadata..."
python scripts/collect_and_store_metadata.py

echo "Metadata collection and storage completed!"
