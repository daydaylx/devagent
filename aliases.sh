#!/bin/bash
# DevAgent CLI Aliases
# Add these to your ~/.bashrc, ~/.zshrc, or source this file directly

# Core DevAgent commands
alias da='devagent'
alias das='devagent scan'
alias dac='devagent check'
alias dap='devagent propose'
alias daa='devagent apply'

# Quick scan current directory
alias scan='devagent scan .'

# Check current project
alias check='devagent check .'

# Propose with common goals (you'll still need --touch)
alias fix='devagent propose --goal "Fix bugs and improve error handling"'
alias refactor='devagent propose --goal "Refactor code for better maintainability"'
alias optimize='devagent propose --goal "Optimize performance and reduce complexity"'
alias test='devagent propose --goal "Add comprehensive tests"'
alias docs='devagent propose --goal "Add documentation and comments"'

# Apply latest patch with common options
alias apply='devagent apply patches/latest.patch'
alias apply-commit='devagent apply patches/latest.patch --autocommit'
alias apply-safe='devagent apply patches/latest.patch --revert-on-fail'

# Quick workflows
alias quick-scan='devagent scan . && devagent check .'
alias full-check='devagent scan . && devagent check . && echo "Project scanned and checked!"'

# Development helpers
alias da-help='devagent --help'
alias da-version='devagent --version 2>/dev/null || echo "DevAgent CLI v1.0.0"'

# Git integration aliases
alias git-propose='git status && devagent propose'
alias git-apply='devagent apply patches/latest.patch --autocommit && git log -1 --oneline'

# File operations
alias touch-all='find . -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" | head -10 | xargs -I {} echo "--touch {}"'

# Debugging and logs
alias da-logs='tail -f .agentcache/devagent.log 2>/dev/null || echo "No log file found"'
alias da-cache='ls -la .agentcache/ 2>/dev/null || echo "No cache directory found"'
alias da-patches='ls -la patches/ 2>/dev/null || echo "No patches directory found"'

# Functions for more complex operations
da-propose-file() {
    if [ -z "$1" ]; then
        echo "Usage: da-propose-file <file> [goal]"
        echo "Example: da-propose-file src/api.ts 'Add error handling'"
        return 1
    fi
    
    local file="$1"
    local goal="${2:-Improve code quality and add error handling}"
    
    if [ ! -f "$file" ]; then
        echo "Error: File '$file' not found"
        return 1
    fi
    
    devagent propose --goal "$goal" --touch "$file"
}

da-propose-dir() {
    if [ -z "$1" ]; then
        echo "Usage: da-propose-dir <directory> [goal] [file-pattern]"
        echo "Example: da-propose-dir src/ 'Refactor components' '*.tsx'"
        return 1
    fi
    
    local dir="$1"
    local goal="${2:-Refactor and improve code quality}"
    local pattern="${3:-*.{ts,tsx,js,jsx,py}}"
    
    if [ ! -d "$dir" ]; then
        echo "Error: Directory '$dir' not found"
        return 1
    fi
    
    local files=$(find "$dir" -name "$pattern" -type f | head -5)
    if [ -z "$files" ]; then
        echo "No files found matching pattern '$pattern' in '$dir'"
        return 1
    fi
    
    local touch_args=""
    while IFS= read -r file; do
        touch_args="$touch_args --touch $file"
    done <<< "$files"
    
    echo "Proposing changes for files in $dir..."
    eval "devagent propose --goal \"$goal\" $touch_args"
}

da-workflow() {
    local goal="$1"
    local files="$2"
    
    if [ -z "$goal" ] || [ -z "$files" ]; then
        echo "Usage: da-workflow '<goal>' '<file1> [file2] ...'"
        echo "Example: da-workflow 'Add error handling' 'src/api.ts src/utils.ts'"
        return 1
    fi
    
    echo "🔍 Scanning project..."
    devagent scan . || return 1
    
    echo "✅ Running checks..."
    devagent check . || echo "⚠️  Some checks failed, continuing anyway..."
    
    echo "🤖 Generating AI proposal..."
    local touch_args=""
    for file in $files; do
        if [ -f "$file" ]; then
            touch_args="$touch_args --touch $file"
        else
            echo "⚠️  File not found: $file"
        fi
    done
    
    if [ -n "$touch_args" ]; then
        eval "devagent propose --goal \"$goal\" $touch_args"
        echo "✨ Proposal generated! Review with: cat patches/latest.patch"
        echo "📦 Apply with: apply-safe"
    else
        echo "❌ No valid files provided"
        return 1
    fi
}

da-status() {
    echo "📊 DevAgent Status:"
    echo "=================="
    
    if [ -d ".agentcache" ]; then
        echo "✅ Cache directory: .agentcache/"
        if [ -f ".agentcache/index.json" ]; then
            local file_count=$(jq '.total_files // 0' .agentcache/index.json 2>/dev/null || echo "unknown")
            echo "📁 Indexed files: $file_count"
        fi
        if [ -f ".agentcache/checks.json" ]; then
            local status=$(jq -r '.overall_status // "unknown"' .agentcache/checks.json 2>/dev/null || echo "unknown")
            echo "🔍 Last check status: $status"
        fi
    else
        echo "❌ No cache found (run 'das' to scan)"
    fi
    
    if [ -d "patches" ]; then
        local patch_count=$(ls patches/*.patch 2>/dev/null | wc -l)
        echo "📝 Patches created: $patch_count"
        if [ -f "patches/latest.patch" ]; then
            echo "🆕 Latest patch available"
        fi
    else
        echo "📝 No patches created yet"
    fi
    
    if command -v devagent >/dev/null 2>&1; then
        echo "🚀 DevAgent CLI: Ready"
    else
        echo "❌ DevAgent CLI: Not found in PATH"
    fi
}

# Help function
da-aliases() {
    echo "DevAgent CLI Aliases:"
    echo "==================="
    echo
    echo "Basic Commands:"
    echo "  da              - devagent"
    echo "  das             - devagent scan"
    echo "  dac             - devagent check"  
    echo "  dap             - devagent propose"
    echo "  daa             - devagent apply"
    echo
    echo "Quick Actions:"
    echo "  scan            - scan current directory"
    echo "  check           - check current project"
    echo "  apply           - apply latest patch"
    echo "  apply-commit    - apply and auto-commit"
    echo "  apply-safe      - apply with revert on fail"
    echo
    echo "Proposal Shortcuts:"
    echo "  fix             - propose bug fixes"
    echo "  refactor        - propose refactoring"
    echo "  optimize        - propose optimizations"
    echo "  test            - propose adding tests"
    echo "  docs            - propose documentation"
    echo
    echo "Workflows:"
    echo "  quick-scan      - scan and check"
    echo "  full-check      - comprehensive project check"
    echo
    echo "Functions:"
    echo "  da-propose-file <file> [goal]      - propose changes for one file"
    echo "  da-propose-dir <dir> [goal]        - propose changes for directory"
    echo "  da-workflow '<goal>' '<files>'     - full scan → check → propose workflow"
    echo "  da-status                          - show DevAgent project status"
    echo "  da-aliases                         - show this help"
    echo
    echo "Debugging:"
    echo "  da-logs         - tail log file"
    echo "  da-cache        - show cache contents"
    echo "  da-patches      - show patches"
}

# Auto-completion for common goals (bash)
if [ -n "$BASH_VERSION" ]; then
    _da_propose_goals="
        'Fix bugs and improve error handling'
        'Refactor code for better maintainability'  
        'Optimize performance and reduce complexity'
        'Add comprehensive tests'
        'Add documentation and comments'
        'Improve type safety'
        'Add input validation'
        'Enhance error messages'
        'Implement missing features'
        'Update dependencies'
    "
    
    complete -W "$_da_propose_goals" fix refactor optimize test docs
fi

echo "✅ DevAgent aliases loaded! Type 'da-aliases' for help."