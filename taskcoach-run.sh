#!/bin/bash
# TaskCoach launcher with virtual environment
# This script activates the virtual environment and runs TaskCoach

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run setup_bookworm.sh first to set up the virtual environment"
    exit 1
fi

source "$VENV_PATH/bin/activate"
cd "$SCRIPT_DIR"
python3 taskcoach.py "$@"
