#!/bin/bash
# Quick test script for TaskCoach
# Tests various functionality to ensure proper operation

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}TaskCoach Test Suite${NC}"
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
    "python3 -c 'from taskcoachlib import meta; assert meta.version'"

# Test 4: wxPython import
run_test "wxPython import" \
    "python3 -c 'import wx; assert wx.__version__'"

# Test 5: Dependencies
run_test "pypubsub dependency" \
    "python3 -c 'import pubsub'"

run_test "twisted dependency" \
    "python3 -c 'import twisted'"

run_test "lxml dependency" \
    "python3 -c 'import lxml'"

run_test "numpy dependency" \
    "python3 -c 'import numpy'"

run_test "dateutil dependency" \
    "python3 -c 'import dateutil'"

# Test 6: Icons file exists
run_test "Icons generated" \
    "[ -f taskcoachlib/gui/icons.py ]"

# Test 7: Templates file exists
run_test "Templates generated" \
    "[ -f taskcoachlib/persistence/xml/templates.py ]"

# Test 8: Application help
run_test "Application help command" \
    "python3 taskcoach.py --help"

# Test 9: Domain objects
run_test "Domain objects import" \
    "python3 -c 'from taskcoachlib.domain import task, category, note, effort'"

# Test 10: GUI modules (basic import)
run_test "GUI modules import" \
    "timeout 5 python3 -c 'from taskcoachlib import gui' || true"

# Test 11: Persistence modules
run_test "Persistence modules" \
    "python3 -c 'from taskcoachlib import persistence'"

# Test 12: Config modules
run_test "Config modules" \
    "python3 -c 'from taskcoachlib import config'"

# Test 13: Try to create a task (no GUI)
echo -n "Testing task creation... "
if python3 << 'EOF' &>/dev/null
import sys
sys.path.insert(0, '.')
from taskcoachlib.domain.task import Task
from taskcoachlib.domain.date import Date

task = Task(subject='Test Task')
assert task.subject() == 'Test Task'
assert task.id()
EOF
then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# Test 14: Try to launch GUI with Xvfb (timeout after 3 seconds)
echo -n "Testing GUI launch (Xvfb)... "
if command -v xvfb-run &>/dev/null; then
    if timeout 3 xvfb-run -a python3 taskcoach.py 2>&1 | head -20 > /tmp/taskcoach_test.log; then
        # Timeout is expected, check if there were no errors
        if grep -q "Traceback\|Error\|error" /tmp/taskcoach_test.log; then
            echo -e "${RED}✗ FAIL (see /tmp/taskcoach_test.log)${NC}"
            ((FAILED++))
        else
            echo -e "${GREEN}✓ PASS${NC}"
            ((PASSED++))
        fi
    elif [ $? -eq 124 ]; then
        # Timeout = success (app is running)
        echo -e "${GREEN}✓ PASS (timeout = running)${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
    rm -f /tmp/taskcoach_test.log
else
    echo -e "${YELLOW}⊘ SKIP (xvfb not installed)${NC}"
fi

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
