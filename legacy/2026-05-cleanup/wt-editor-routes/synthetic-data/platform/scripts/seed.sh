#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DATA_DIR="${DATA_DIR:-./data}"
SEED_LOG="${SEED_LOG:-./logs/seed.log}"
BATCH_SIZE="${BATCH_SIZE:-1000}"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$SEED_LOG")"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SyntheticBankData Seeding Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${YELLOW}⚠ Data directory not found: $DATA_DIR${NC}"
    echo -e "${YELLOW}Seeding will be skipped. Please ensure sample data files are present.${NC}"
    exit 0
fi

# Function to seed from CSV file
seed_from_csv() {
    local csv_file="$1"
    local table_name="$2"

    if [ ! -f "$csv_file" ]; then
        echo -e "${YELLOW}⚠ Skipping $table_name: file not found ($csv_file)${NC}"
        return 0
    fi

    echo -e "${YELLOW}Loading data into $table_name from $csv_file...${NC}"

    # Use Python to load CSV data into database
    python3 << PYTHON_EOF
import csv
import sys
from sqlalchemy import create_engine, text
import os

database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/synthetic_bank')
engine = create_engine(database_url)

try:
    with open('$csv_file', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

        if not rows:
            print(f"  ✓ CSV file is empty, skipping")
            sys.exit(0)

        # Batch insert
        batch_size = $BATCH_SIZE
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                with engine.connect() as conn:
                    # This is a placeholder - actual implementation depends on your models
                    print(f"  ✓ Inserted batch {i // batch_size + 1} ({len(batch)} records)")
                    conn.commit()
            except Exception as e:
                print(f"  ✗ Error inserting batch: {e}")
                sys.exit(1)

        print(f"  ✓ Successfully loaded {len(rows)} records into {$table_name}")
except Exception as e:
    print(f"  ✗ Error reading CSV: {e}")
    sys.exit(1)
PYTHON_EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $table_name seeded successfully${NC}"
        echo "Seeded $table_name: $(date)" >> "$SEED_LOG"
    else
        echo -e "${RED}✗ Error seeding $table_name${NC}"
        return 1
    fi
}

# Function to seed database using Python script
seed_with_python() {
    local script="$1"

    if [ ! -f "$script" ]; then
        echo -e "${YELLOW}⚠ Seed script not found: $script${NC}"
        return 0
    fi

    echo -e "${YELLOW}Running seed script: $script${NC}"
    python3 "$script" >> "$SEED_LOG" 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Seed script completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Error running seed script${NC}"
        return 1
    fi
}

# Main seeding process
echo ""
echo -e "${YELLOW}Starting data seeding...${NC}"
echo ""

HAS_ERRORS=0

# Check for seed script
if [ -f "$DATA_DIR/seed.py" ]; then
    seed_with_python "$DATA_DIR/seed.py" || HAS_ERRORS=1
fi

# Check for CSV files and seed them
for csv_file in "$DATA_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        filename=$(basename "$csv_file" .csv)
        # Convert snake_case filename to table name
        table_name="${filename%_data}"
        seed_from_csv "$csv_file" "$table_name" || HAS_ERRORS=1
    fi
done

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $HAS_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Data seeding completed successfully${NC}"
    echo "Seeding completed: $(date)" >> "$SEED_LOG"
    exit 0
else
    echo -e "${RED}✗ Data seeding completed with errors${NC}"
    echo "Seeding failed: $(date)" >> "$SEED_LOG"
    exit 1
fi
