#!/bin/bash
# DNSimple DNS setup for Azure Static Web Apps
# Usage: ./setup-dns.sh <validation-token>
#
# Prerequisites:
# - curl installed
# - DNSimple API token and account ID configured below
# - Azure Static Web App already deployed

set -euo pipefail

# Configuration
DNSIMPLE_TOKEN="${DNSIMPLE_TOKEN:-dnsimple_u_BDESWPB2dSxQnWkFYSbub5Sjn8JUDnmA}"
DNSIMPLE_ACCOUNT_ID="${DNSIMPLE_ACCOUNT_ID:-}"
DOMAIN="stepinto.dev"
SWA_HOSTNAME="stepinto-dev-blog.azurestaticapps.net"

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No colour

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check for validation token argument
VALIDATION_TOKEN="${1:-}"

if [[ -z "$VALIDATION_TOKEN" ]]; then
    log_warn "No validation token provided."
    echo ""
    echo "To get the validation token:"
    echo "  1. Go to Azure Portal → Static Web App → Custom domains"
    echo "  2. Click 'Add' and enter: $DOMAIN"
    echo "  3. Copy the TXT record value shown"
    echo ""
    echo "Usage: $0 <validation-token>"
    echo ""
    read -p "Enter validation token (or press Enter to skip TXT record): " VALIDATION_TOKEN
fi

# Get account ID if not set
if [[ -z "$DNSIMPLE_ACCOUNT_ID" ]]; then
    log_info "Fetching DNSimple account ID..."
    ACCOUNT_RESPONSE=$(curl -s -H "Authorization: Bearer $DNSIMPLE_TOKEN" \
        "https://api.dnsimple.com/v2/whoami")
    
    DNSIMPLE_ACCOUNT_ID=$(echo "$ACCOUNT_RESPONSE" | grep -o '"account":{"id":[0-9]*' | grep -o '[0-9]*' || true)
    
    if [[ -z "$DNSIMPLE_ACCOUNT_ID" ]]; then
        # Try user account
        DNSIMPLE_ACCOUNT_ID=$(echo "$ACCOUNT_RESPONSE" | grep -o '"user":{"id":[0-9]*' | grep -o '[0-9]*' || true)
    fi
    
    if [[ -z "$DNSIMPLE_ACCOUNT_ID" ]]; then
        log_error "Could not determine account ID. Response:"
        echo "$ACCOUNT_RESPONSE"
        exit 1
    fi
    
    log_info "Using account ID: $DNSIMPLE_ACCOUNT_ID"
fi

API_BASE="https://api.dnsimple.com/v2/$DNSIMPLE_ACCOUNT_ID/zones/$DOMAIN/records"

# Function to create DNS record
create_record() {
    local name="$1"
    local type="$2"
    local content="$3"
    local ttl="${4:-3600}"
    
    local display_name="${name:-@}"
    log_info "Creating $type record: $display_name → $content"
    
    local response=$(curl -s -X POST \
        -H "Authorization: Bearer $DNSIMPLE_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$name\",
            \"type\": \"$type\",
            \"content\": \"$content\",
            \"ttl\": $ttl
        }" \
        "$API_BASE")
    
    if echo "$response" | grep -q '"id":'; then
        log_info "✓ $type record created successfully"
        return 0
    elif echo "$response" | grep -q 'already been taken'; then
        log_warn "$type record already exists, skipping"
        return 0
    else
        log_error "Failed to create $type record:"
        echo "$response" | head -c 500
        echo ""
        return 1
    fi
}

# Function to list existing records
list_records() {
    log_info "Current DNS records for $DOMAIN:"
    curl -s -H "Authorization: Bearer $DNSIMPLE_TOKEN" "$API_BASE" | \
        grep -oE '"name":"[^"]*","type":"[^"]*","content":"[^"]*"' | \
        sed 's/"name":"/@/g; s/","type":"/ /g; s/","content":"/ → /g; s/"//g' | \
        while read line; do echo "  $line"; done
}

echo ""
echo "======================================"
echo "DNSimple DNS Setup for Azure SWA"
echo "======================================"
echo "Domain: $DOMAIN"
echo "Target: $SWA_HOSTNAME"
echo ""

# List current records
list_records
echo ""

# Create ALIAS record for root domain
log_info "Setting up root domain ($DOMAIN)..."
create_record "" "ALIAS" "$SWA_HOSTNAME"

# Create TXT record for Azure validation (if token provided)
if [[ -n "$VALIDATION_TOKEN" ]]; then
    log_info "Setting up validation TXT record..."
    create_record "" "TXT" "$VALIDATION_TOKEN"
else
    log_warn "Skipping TXT record (no validation token provided)"
fi

# Create www CNAME redirect
log_info "Setting up www redirect..."
create_record "www" "CNAME" "$SWA_HOSTNAME"

echo ""
echo "======================================"
log_info "DNS setup complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Wait for DNS propagation (usually 5-15 minutes)"
echo "  2. Verify in Azure Portal that the custom domain shows 'Ready'"
echo "  3. SSL certificate will be provisioned automatically"
echo ""
echo "To check DNS propagation:"
echo "  dig $DOMAIN"
echo "  dig www.$DOMAIN"
echo ""

