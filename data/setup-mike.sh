#!/bin/bash
# Setup Mike's persona — run after filling in credentials.json
set -e

PERSONA_DIR="$(dirname "$0")/personas/mike"
CREDS="$PERSONA_DIR/credentials.json"

echo "=== Mike Anderson — Persona Setup ==="
echo ""

# Check credentials
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required"
    exit 1
fi

EMAIL=$(python3 -c "import json; print(json.load(open('$CREDS'))['google']['email'])")
if [ -z "$EMAIL" ] || [ "$EMAIL" = "" ]; then
    echo "⚠  No Google email set in $CREDS"
    echo "   1. Create a Google account for Mike"
    echo "   2. Fill in 'email' and 'app_password' in credentials.json"
    echo "   3. Run this script again"
    exit 1
fi

echo "✓ Google account: $EMAIL"
echo ""
echo "Loading persona data..."
echo "  - $(python3 -c "import json; print(len(json.load(open('$PERSONA_DIR/emails.json'))))" ) emails"
echo "  - $(python3 -c "import json; print(len(json.load(open('$PERSONA_DIR/calendar.json'))))" ) calendar events"
echo "  - $(python3 -c "import json; d=json.load(open('$PERSONA_DIR/persona.json')); print(len(d['contacts']))" ) contacts"
echo ""
echo "Ready to populate services. Run with --populate to push data:"
echo "  ./setup-mike.sh --populate"
echo ""

if [ "$1" = "--populate" ]; then
    echo "Populating services... (requires credentials)"
    python3 "$PERSONA_DIR/populate.py"
fi
