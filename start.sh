#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

status() {
    echo -e "${GREEN}[*]${NC} $1"
}

error() {
    echo -e "${YELLOW}[!]${NC} $1"
    exit 1
}

if ! command -v python3 &> /dev/null; then
    error "Python 3 is required but not installed. Please install Python 3 and try again."
fi
if ! command -v pip3 &> /dev/null; then
    error "pip3 is required but not installed. Please install pip3 and try again."
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
if [ ! -d "$VENV_DIR" ]; then
    status "Creating virtual environment..."
    python3 -m venv "$VENV_DIR" || error "Failed to create virtual environment"
    
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    elif [ -f "$VENV_DIR/Scripts/activate" ]; then
        source "$VENV_DIR/Scripts/activate"
    else
        error "Could not find virtual environment activation script"
    fi
    
    status "Upgrading pip..."
    pip install --upgrade pip || error "Failed to upgrade pip"
    
    if [ -f "$REQUIREMENTS" ]; then
        status "Installing dependencies..."
        pip install -r "$REQUIREMENTS" || error "Failed to install dependencies"
    else
        status "Installing required packages..."
        pip install requests || error "Failed to install required packages"
    fi
    
    deactivate
    status "Virtual environment setup complete."
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
else
    error "Could not activate virtual environment"
fi

TOKENS_FILE="$SCRIPT_DIR/tokens.txt"
if [ ! -f "$TOKENS_FILE" ] || [ ! -s "$TOKENS_FILE" ]; then
    echo -e "${YELLOW}[!] No tokens found. Would you like to run the token generator?${NC}"
    read -p "(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        status "Starting token generator..."
        python3 "$SCRIPT_DIR/token-gen/src/main.py" || error "Token generator failed"
        
        if [ ! -f "$TOKENS_FILE" ] || [ ! -s "$TOKENS_FILE" ]; then
            error "No tokens were generated. Please run the token generator manually."
        fi
    else
        error "Tokens are required to run the bot. Please run the token generator first."
    fi
fi

status "Starting Xbox Follower Bot..."
python3 "$SCRIPT_DIR/src/main.py"

deactivate 2>/dev/null || true
