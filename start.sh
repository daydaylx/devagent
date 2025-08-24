#!/bin/bash

# DevAgent CLI - Start Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning ".env not found, copying from .env.example"
        cp .env.example .env
        print_warning "Please edit .env and add your OPENROUTER_API_KEY"
    else
        print_warning "Creating basic .env file"
        cat > .env << EOF
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct:free
OPENROUTER_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
EOF
        print_warning "Please edit .env and add your OPENROUTER_API_KEY"
    fi
fi

# Install package in development mode
print_info "Installing DevAgent CLI..."
pip install -e .

print_success "DevAgent CLI setup complete!"
print_info "Available commands:"
echo "  devagent gui        - Launch graphical user interface"
echo "  devagent scan       - Scan project and build context"
echo "  devagent check      - Run health checks"
echo "  devagent propose    - Generate AI code proposals"
echo "  devagent apply      - Apply patches"
echo "  devagent-gui        - Direct GUI launcher"

# Check for API key
if grep -q "your_api_key_here" .env 2>/dev/null; then
    print_warning "Remember to set your OPENROUTER_API_KEY in .env file"
fi

print_info "To get started:"
echo "  devagent gui        - For graphical interface"
echo "  devagent scan       - For command line usage"