#!/bin/bash
# Workflow Validation Script
# Validates GitHub Actions workflow files for syntax and common issues

set -e

echo "🔍 Validating GitHub Actions Workflows"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Counter for issues
ERRORS=0
WARNINGS=0

# Function to check file
check_workflow() {
    local file=$1
    echo "📄 Checking: $file"

    # Check if file exists
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ File not found${NC}"
        ((ERRORS++))
        return
    fi

    # Check YAML syntax using Python
    if command -v python3 &> /dev/null; then
        if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo -e "${RED}❌ Invalid YAML syntax${NC}"
            ((ERRORS++))
            return
        else
            echo -e "${GREEN}✅ Valid YAML syntax${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Python not available, skipping YAML validation${NC}"
        ((WARNINGS++))
    fi

    # Check for common issues

    # 1. Check for hardcoded secrets
    if grep -q "password:" "$file" | grep -v "secrets\." | grep -v "#"; then
        echo -e "${YELLOW}⚠️  Warning: Potential hardcoded password found${NC}"
        ((WARNINGS++))
    fi

    # 2. Check for proper checkout action
    if ! grep -q "actions/checkout@v" "$file"; then
        echo -e "${YELLOW}⚠️  Warning: No checkout action found${NC}"
        ((WARNINGS++))
    fi

    # 3. Check for version pinning in actions
    if grep -q "actions/.*@main" "$file" || grep -q "actions/.*@master" "$file"; then
        echo -e "${YELLOW}⚠️  Warning: Actions using branch names instead of versions${NC}"
        ((WARNINGS++))
    fi

    # 4. Check for required permissions
    if grep -q "packages: write" "$file"; then
        if ! grep -q "contents: read" "$file"; then
            echo -e "${YELLOW}⚠️  Warning: packages:write without contents:read${NC}"
            ((WARNINGS++))
        fi
    fi

    echo ""
}

# Check all workflow files
echo "Checking workflow files..."
echo ""

for workflow in .github/workflows/*.yml .github/workflows/*.yaml; do
    if [ -f "$workflow" ]; then
        check_workflow "$workflow"
    fi
done

# Summary
echo "======================================"
echo "📊 Validation Summary"
echo "======================================"
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All workflows passed validation!${NC}"
    exit 0
else
    echo -e "${RED}❌ Validation failed with $ERRORS error(s)${NC}"
    exit 1
fi
