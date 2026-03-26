#!/bin/bash
set -e
echo "Starting recovery script on server..."

# Find the latest backup that `deploy.sh` created
LATEST_BACKUP=$(ls -td /home/ubuntu/backups/monorepo-* | head -n 1)
echo "Latest backup found: $LATEST_BACKUP"

# Restore stock_data.csv from backup
cd /home/ubuntu/aktien-tool2
cp "$LATEST_BACKUP/stock_data.csv" ./stock_data.csv
echo "Restored stock_data.csv from backup."

# Stop tracking stock_data.csv so this never happens again
git rm --cached stock_data.csv || true
if ! grep -q "stock_data.csv" .gitignore; then
    echo "stock_data.csv" >> .gitignore
fi

# Commit the .gitignore update and the removal of the CSV
git commit -am "Stop tracking stock_data.csv to prevent data loss on deploy" || true
git push origin HEAD:main || true

echo "Data recovery and tracking fix complete!"
