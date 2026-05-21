#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/synthetic_bank_${TIMESTAMP}.sql"
BACKUP_COMPRESSED="${BACKUP_FILE}.gz"

# Database configuration
DB_HOST="${DATABASE_HOST:-db}"
DB_PORT="${DATABASE_PORT:-5432}"
DB_NAME="${DATABASE_NAME:-synthetic_bank}"
DB_USER="${DATABASE_USER:-postgres}"
DB_PASSWORD="${DATABASE_PASSWORD:-}"

# AWS S3 configuration (optional)
AWS_S3_ENABLED="${AWS_S3_ENABLED:-false}"
AWS_S3_BUCKET="${AWS_S3_BUCKET:-}"
AWS_S3_PREFIX="${AWS_S3_PREFIX:-backups}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Retention policy
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-10}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SyntheticBankData Database Backup Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  Backup directory: $BACKUP_DIR"
echo "  Timestamp: $TIMESTAMP"
echo ""

# Function to create backup
create_backup() {
    echo -e "${YELLOW}Creating database backup...${NC}"

    # Prepare environment for pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    # Run pg_dump with custom format for better compression and flexibility
    if pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F c \
        -v > "$BACKUP_FILE" 2>&1; then
        echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
        return 0
    else
        echo -e "${RED}✗ Error creating backup${NC}"
        return 1
    fi
}

# Function to compress backup
compress_backup() {
    echo -e "${YELLOW}Compressing backup...${NC}"

    if gzip -f "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Backup compressed: $BACKUP_COMPRESSED${NC}"
        # Display file size
        if command -v du &> /dev/null; then
            local size=$(du -h "$BACKUP_COMPRESSED" | cut -f1)
            echo "  Size: $size"
        fi
        return 0
    else
        echo -e "${RED}✗ Error compressing backup${NC}"
        return 1
    fi
}

# Function to upload to S3
upload_to_s3() {
    if [ "$AWS_S3_ENABLED" != "true" ] || [ -z "$AWS_S3_BUCKET" ]; then
        echo -e "${YELLOW}⚠ S3 upload disabled${NC}"
        return 0
    fi

    echo -e "${YELLOW}Uploading backup to S3...${NC}"

    if command -v aws &> /dev/null; then
        local s3_path="s3://${AWS_S3_BUCKET}/${AWS_S3_PREFIX}/synthetic_bank_${TIMESTAMP}.sql.gz"

        if aws s3 cp "$BACKUP_COMPRESSED" "$s3_path" \
            --region "$AWS_REGION" \
            --storage-class STANDARD_IA \
            --sse AES256; then
            echo -e "${GREEN}✓ Backup uploaded to S3: $s3_path${NC}"
            return 0
        else
            echo -e "${RED}✗ Error uploading to S3${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ AWS CLI not installed, skipping S3 upload${NC}"
        return 0
    fi
}

# Function to create backup metadata
create_metadata() {
    local metadata_file="${BACKUP_DIR}/synthetic_bank_${TIMESTAMP}.metadata"

    cat > "$metadata_file" << EOF
Backup Metadata
===============
Timestamp: $TIMESTAMP
Database: $DB_NAME
Host: $DB_HOST
Port: $DB_PORT
Backup File: $(basename "$BACKUP_COMPRESSED")
File Size: $(du -h "$BACKUP_COMPRESSED" | cut -f1)
Created: $(date)

Backup Statistics
=================
EOF

    # Append backup statistics if available
    if command -v pg_restore &> /dev/null; then
        echo "Table count: $(pg_restore -l "$BACKUP_COMPRESSED" 2>/dev/null | grep "TABLE" | wc -l)" >> "$metadata_file" || true
    fi

    echo -e "${GREEN}✓ Metadata file created: $metadata_file${NC}"
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${YELLOW}Cleaning up old backups...${NC}"

    local backup_count=0
    local deleted_count=0

    # Count existing backups
    backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -name "synthetic_bank_*.sql.gz" -type f | wc -l)
    echo "  Current backup count: $backup_count"

    # Delete backups older than retention period
    if [ "$RETENTION_DAYS" -gt 0 ]; then
        echo "  Removing backups older than $RETENTION_DAYS days..."
        while IFS= read -r old_backup; do
            rm -f "$old_backup"
            rm -f "${old_backup%.gz}.metadata" 2>/dev/null || true
            deleted_count=$((deleted_count + 1))
            echo "    Deleted: $(basename "$old_backup")"
        done < <(find "$BACKUP_DIR" -maxdepth 1 -name "synthetic_bank_*.sql.gz" -type f -mtime +"$RETENTION_DAYS")
    fi

    # Keep only the latest N backups
    echo "  Keeping latest $BACKUP_RETENTION_COUNT backups..."
    local count=0
    while IFS= read -r old_backup; do
        if [ $count -ge $((BACKUP_RETENTION_COUNT - 1)) ]; then
            rm -f "$old_backup"
            rm -f "${old_backup%.gz}.metadata" 2>/dev/null || true
            deleted_count=$((deleted_count + 1))
            echo "    Deleted: $(basename "$old_backup")"
        fi
        count=$((count + 1))
    done < <(find "$BACKUP_DIR" -maxdepth 1 -name "synthetic_bank_*.sql.gz" -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)

    if [ $deleted_count -gt 0 ]; then
        echo -e "${GREEN}✓ Deleted $deleted_count old backup(s)${NC}"
    else
        echo -e "${GREEN}✓ No old backups to delete${NC}"
    fi
}

# Function to verify backup
verify_backup() {
    echo -e "${YELLOW}Verifying backup integrity...${NC}"

    if command -v pg_restore &> /dev/null; then
        if pg_restore -l "$BACKUP_COMPRESSED" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backup verification passed${NC}"
            return 0
        else
            echo -e "${RED}✗ Backup verification failed${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ pg_restore not available, skipping verification${NC}"
        return 0
    fi
}

# Main execution
echo ""
HAS_ERRORS=0

# Step 1: Create backup
create_backup || HAS_ERRORS=1

# Step 2: Compress backup
if [ $HAS_ERRORS -eq 0 ]; then
    compress_backup || HAS_ERRORS=1
fi

# Step 3: Verify backup
if [ $HAS_ERRORS -eq 0 ]; then
    verify_backup || HAS_ERRORS=1
fi

# Step 4: Create metadata
if [ $HAS_ERRORS -eq 0 ]; then
    create_metadata
fi

# Step 5: Upload to S3 (if enabled)
if [ $HAS_ERRORS -eq 0 ]; then
    upload_to_s3
fi

# Step 6: Cleanup old backups
cleanup_old_backups

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $HAS_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    echo ""
    echo "Backup Summary:"
    echo "  Location: $BACKUP_COMPRESSED"
    echo "  Size: $(du -h "$BACKUP_COMPRESSED" | cut -f1)"
    echo "  Timestamp: $TIMESTAMP"
    exit 0
else
    echo -e "${RED}✗ Backup completed with errors${NC}"
    exit 1
fi
