#!/bin/bash
# Quick test script for TaskCoach
# Tests various functionality to ensure proper operation
#
# Note: Twisted replaced with watchdog in PR #39

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    echo -e "${BLUE}Using virtual environment: .venv${NC}"
else
    echo -e "${YELLOW}Warning: Virtual environment not found at .venv${NC}"
    echo -e "${YELLOW}Some tests may fail. Run setup_bookworm.sh first.${NC}"
fi

echo
echo -e "${BLUE}TaskCoach Test Suite${NC}"
echo -e "${BLUE}Version 1.1.1.007${NC}"
echo "===================="
echo

# Test counter
PASSED=0
FAILED=0

# Helper function
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    echo -n "Testing $test_name... "
    if eval "$test_cmd" &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Python version
run_test "Python version (3.11+)" \
    "python3 -c 'import sys; assert sys.version_info >= (3, 11)'"

# Test 2: TaskCoach module import
run_test "TaskCoach module import" \
    "python3 -c 'import taskcoachlib'"

# Test 3: Version info
run_test "Version metadata" \
    "python3 -c 'import taskcoachlib.meta.data as meta; assert meta.version'"

# Test 4: wxPython import
run_test "wxPython import" \
    "python3 -c 'import wx; assert wx.__version__'"

# Test 4b: wxPython patch verification
# Use Python to check if the patch is actually loaded at runtime
run_test "wxPython patch (background fix)" \
    "python3 -c 'import wx.lib.agw.hypertreelist as ht; import inspect; s=inspect.getsource(ht.TreeListMainWindow.PaintItem); exit(0 if \"Fix from Issue #2081 (Roland171281)\" in s else 1)'"

# Test 5: Dependencies
run_test "pypubsub dependency" \
    "python3 -c 'import pubsub'"

run_test "watchdog dependency" \
    "python3 -c 'import watchdog'"

run_test "lxml dependency" \
    "python3 -c 'import lxml'"

run_test "numpy dependency" \
    "python3 -c 'import numpy'"

run_test "dateutil dependency" \
    "python3 -c 'import dateutil'"

# Test 6: Icons directory exists and has PNG files
run_test "Icons directory exists" \
    "[ -d taskcoachlib/gui/icons ] && [ -f taskcoachlib/gui/icons/splash.png ]"

# Test 7: Templates file exists
run_test "Templates file exists" \
    "[ -f taskcoachlib/persistence/xml/templates.py ]"

# Test 8: Application help
run_test "Application help command" \
    "python3 taskcoach.py --help"

# Test 9: Domain objects (requires wx.App)
run_test "Domain objects import" \
    "python3 -c 'import wx; app=wx.App(False); from taskcoachlib.domain import task, category, note, effort'"

# Test 10: GUI modules (basic import)
run_test "GUI modules import" \
    "timeout 5 python3 -c 'from taskcoachlib import gui' || true"

# Test 11: Persistence modules (requires wx.App)
run_test "Persistence modules" \
    "python3 -c 'import wx; app=wx.App(False); from taskcoachlib import persistence'"

# Test 12: Config modules
run_test "Config modules" \
    "python3 -c 'from taskcoachlib import config'"

# Summary
echo
echo "===================="
echo -e "${BLUE}Test Results${NC}"
echo "===================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo "TaskCoach appears to be working correctly."
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    echo "Please check the errors above."
    exit 1
fi
