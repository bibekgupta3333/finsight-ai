#!/bin/bash

# FinSight AI - DVC Local Testing Script
# This script helps test the DVC pipeline locally
# Run after configuring DagsHub credentials

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo " FinSight AI - DVC Pipeline Local Testing"
echo "======================================================================"
echo ""

# Get DVC binary path
if [ -f ".venv/bin/dvc" ]; then
    DVC_BIN=".venv/bin/dvc"
    PYTHON_BIN=".venv/bin/python"
elif command -v dvc &> /dev/null; then
    DVC_BIN="dvc"
    PYTHON_BIN="python"
else
    echo -e "${RED}❌ DVC not found. Please install DVC first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Using DVC: $DVC_BIN"
echo -e "${GREEN}✓${NC} Using Python: $PYTHON_BIN"
echo ""

# Check if we're in the right directory
if [ ! -f "dvc.yaml" ]; then
    echo -e "${RED}❌ dvc.yaml not found. Please run this script from the project root.${NC}"
    exit 1
fi

echo "======================================================================"
echo " Step 1: Verify DVC Configuration"
echo "======================================================================"
echo ""

$DVC_BIN version
echo ""

echo "DVC Remotes:"
$DVC_BIN remote list
echo ""

echo "======================================================================"
echo " Step 2: Verify Pipeline DAG"
echo "======================================================================"
echo ""

if $DVC_BIN dag > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} DVC pipeline is valid"
    $DVC_BIN dag
    echo ""
else
    echo -e "${RED}❌ DVC pipeline has errors${NC}"
    $DVC_BIN dag
    exit 1
fi

echo "======================================================================"
echo " Step 3: Check Pipeline Status"
echo "======================================================================"
echo ""

$DVC_BIN status | head -20
echo ""

echo "======================================================================"
echo " Step 4: Run Data Quality Check (Optional)"
echo "======================================================================"
echo ""

read -p "Run data quality validation? (y/N): " run_quality
if [[ $run_quality =~ ^[Yy]$ ]]; then
    echo "Running quality check..."
    $PYTHON_BIN backend/scripts/data_quality_check.py
    echo ""

    if [ -f "data/analysis/data_quality_report.json" ]; then
        echo -e "${GREEN}✓${NC} Quality report generated"
        cat data/analysis/data_quality_report.json | $PYTHON_BIN -m json.tool
    fi
else
    echo "Skipping quality check."
fi
echo ""

echo "======================================================================"
echo " Step 5: Test DagsHub Connection (Optional)"
echo "======================================================================"
echo ""

read -p "Test DagsHub push/pull? Requires credentials configured. (y/N): " test_dagshub
if [[ $test_dagshub =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}⚠️  This will attempt to push data to DagsHub.${NC}"
    echo -e "${YELLOW}⚠️  Make sure you have configured credentials:${NC}"
    echo "   dvc remote modify dagshub --local user bibekgupta3333"
    echo "   dvc remote modify dagshub --local password <TOKEN>"
    echo ""

    read -p "Credentials configured? Continue? (y/N): " continue_push
    if [[ $continue_push =~ ^[Yy]$ ]]; then
        echo "Testing DagsHub connection..."

        # Try to push just one .dvc file to test
        if [ -f "data/raw/PS_20174392719_1491204439457_log.csv.dvc" ]; then
            echo "Testing push with raw data file..."
            $DVC_BIN push data/raw/PS_20174392719_1491204439457_log.csv.dvc

            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓${NC} DagsHub push successful!"
                echo ""
                echo "Verify at: https://dagshub.com/bibekgupta3333/finsight-ai/data"
            else
                echo -e "${RED}❌ DagsHub push failed. Check credentials.${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  No .dvc files to push. Run 'dvc add' first.${NC}"
        fi
    else
        echo "Skipping DagsHub test."
    fi
else
    echo "Skipping DagsHub test."
fi
echo ""

echo "======================================================================"
echo " Step 6: Test Pipeline Reproduction (Optional)"
echo "======================================================================"
echo ""

read -p "Test pipeline reproduction (dvc repro)? WARNING: This will regenerate data. (y/N): " test_repro
if [[ $test_repro =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}⚠️  This will run the full DVC pipeline and regenerate outputs.${NC}"
    echo -e "${YELLOW}⚠️  This may take 30+ minutes on M4 Pro.${NC}"
    echo ""

    read -p "Continue? (y/N): " continue_repro
    if [[ $continue_repro =~ ^[Yy]$ ]]; then
        echo "Running pipeline..."
        $DVC_BIN repro

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC} Pipeline reproduction successful!"
            echo ""
            echo "Generated files:"
            ls -lh data/processed/ data/splits/stratified/ data/balanced/ | head -20
        else
            echo -e "${RED}❌ Pipeline reproduction failed.${NC}"
        fi
    else
        echo "Skipping pipeline reproduction."
    fi
else
    echo "Skipping pipeline reproduction."
fi
echo ""

echo "======================================================================"
echo " Summary"
echo "======================================================================"
echo ""
echo -e "${GREEN}✅ DVC pipeline configured and ready${NC}"
echo ""
echo "Next steps:"
echo "  1. Configure DagsHub credentials (if not done)"
echo "     dvc remote modify dagshub --local user bibekgupta3333"
echo "     dvc remote modify dagshub --local password <TOKEN>"
echo ""
echo "  2. Push data to DagsHub"
echo "     $DVC_BIN push"
echo ""
echo "  3. Verify on DagsHub"
echo "     https://dagshub.com/bibekgupta3333/finsight-ai/data"
echo ""
echo "  4. Test data pull (on another machine)"
echo "     git clone https://github.com/bibekgupta3333/finsight-ai.git"
echo "     cd finsight-ai && $DVC_BIN pull"
echo ""
echo "======================================================================"
