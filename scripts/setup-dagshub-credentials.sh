#!/bin/bash

# DagsHub Credentials Configuration Helper
# This script helps you configure DagsHub credentials for DVC

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================================"
echo " DagsHub Credentials Setup for FinSight AI"
echo "======================================================================"
echo ""

# Check if in project root
if [ ! -f "dvc.yaml" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory.${NC}"
    exit 1
fi

# Find DVC binary
if [ -f ".venv/bin/dvc" ]; then
    DVC_BIN=".venv/bin/dvc"
elif command -v dvc &> /dev/null; then
    DVC_BIN="dvc"
else
    echo -e "${RED}❌ DVC not found. Please install DVC first.${NC}"
    exit 1
fi

echo -e "${BLUE}Step 1: Get Your DagsHub Token${NC}"
echo "----------------------------------------------------------------------"
echo ""
echo "1. Visit: https://dagshub.com/user/settings/tokens"
echo "2. Click 'Generate New Token'"
echo "3. Token name: finsight-ai-dvc"
echo "4. Permissions: Select 'repo' (Full access to repositories)"
echo "5. Click 'Generate' and copy the token"
echo ""
echo -e "${YELLOW}⚠️  The token looks like: dagshub_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx${NC}"
echo ""

read -p "Do you have your DagsHub token ready? (y/N): " has_token
echo ""

if [[ ! $has_token =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Please get your token first, then run this script again.${NC}"
    exit 0
fi

echo -e "${BLUE}Step 2: Configure Credentials${NC}"
echo "----------------------------------------------------------------------"
echo ""

# Get username
read -p "DagsHub username (default: bibekgupta3333): " username
username=${username:-bibekgupta3333}

# Get token
echo ""
echo -e "${YELLOW}⚠️  Your token will be stored in .dvc/config.local (gitignored - stays private)${NC}"
echo ""
read -sp "Paste your DagsHub token: " token
echo ""
echo ""

if [ -z "$token" ]; then
    echo -e "${RED}❌ Token cannot be empty.${NC}"
    exit 1
fi

# Configure DVC
echo "Configuring DVC credentials..."
echo ""

$DVC_BIN remote modify dagshub --local user "$username"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to set username.${NC}"
    exit 1
fi

$DVC_BIN remote modify dagshub --local password "$token"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to set token.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Credentials configured successfully!"
echo ""

# Verify
echo -e "${BLUE}Step 3: Verify Configuration${NC}"
echo "----------------------------------------------------------------------"
echo ""

if [ -f ".dvc/config.local" ]; then
    echo -e "${GREEN}✓${NC} .dvc/config.local created"
    echo ""
    echo "Contents (token masked):"
    sed "s/password = .*/password = **********************/" .dvc/config.local
else
    echo -e "${RED}❌ .dvc/config.local not found${NC}"
    exit 1
fi
echo ""

# Test connection
echo -e "${BLUE}Step 4: Test DagsHub Connection${NC}"
echo "----------------------------------------------------------------------"
echo ""

read -p "Test push a small file to DagsHub? (y/N): " test_push

if [[ $test_push =~ ^[Yy]$ ]]; then
    echo ""
    echo "Testing connection..."

    # Check if we have any .dvc files to push
    if [ -f "data/raw/PS_20174392719_1491204439457_log.csv.dvc" ]; then
        echo "Pushing raw data file to DagsHub..."
        $DVC_BIN push data/raw/PS_20174392719_1491204439457_log.csv.dvc -v

        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✅ SUCCESS! Data pushed to DagsHub!${NC}"
            echo ""
            echo "Verify at: https://dagshub.com/$username/finsight-ai/data"
            echo ""
        else
            echo ""
            echo -e "${RED}❌ Push failed. Check your token and permissions.${NC}"
            echo ""
            echo "Troubleshooting:"
            echo "1. Verify token at: https://dagshub.com/user/settings/tokens"
            echo "2. Ensure token has 'repo' permissions"
            echo "3. Check DagsHub repo exists: https://dagshub.com/$username/finsight-ai"
            echo ""
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  No .dvc files found to test push.${NC}"
    fi
else
    echo "Skipping connection test."
fi
echo ""

echo "======================================================================"
echo -e " ${GREEN}✅ DagsHub Credentials Setup Complete!${NC}"
echo "======================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Push all data to DagsHub:"
echo "   $DVC_BIN push"
echo ""
echo "2. Verify on DagsHub:"
echo "   https://dagshub.com/$username/finsight-ai/data"
echo ""
echo "3. Test data pull (optional):"
echo "   cd /tmp && git clone https://github.com/$username/finsight-ai.git test"
echo "   cd test && $DVC_BIN pull"
echo ""
echo "======================================================================"
