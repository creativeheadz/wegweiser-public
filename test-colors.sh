#!/bin/bash

# Color test script
# Tests if your terminal supports ANSI colors

echo "Testing terminal color support..."
echo ""

# Enable color support
export TERM=xterm-256color

# Test colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${RED}This text should be RED${NC}"
echo -e "${GREEN}This text should be GREEN${NC}"
echo -e "${YELLOW}This text should be YELLOW${NC}"
echo -e "${BLUE}This text should be BLUE${NC}"
echo -e "${CYAN}This text should be CYAN${NC}"
echo -e "${MAGENTA}This text should be MAGENTA${NC}"
echo -e "${BOLD}This text should be BOLD${NC}"

echo ""
echo -e "${GREEN}[✓]${NC} This is a success message"
echo -e "${RED}[✗]${NC} This is an error message"
echo -e "${YELLOW}[!]${NC} This is a warning message"
echo -e "${BLUE}[i]${NC} This is an info message"

echo ""
echo "If you see colors above, your terminal supports them!"
echo "If you only see escape codes like \033[0;32m, try:"
echo "  1. Run: export TERM=xterm-256color"
echo "  2. Or add to ~/.bashrc: export TERM=xterm-256color"
