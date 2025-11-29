#!/bin/bash
set -euo pipefail

# ============================================================================
# Multi-MCP Installation Script
#
# Handles environment setup, dependency installation, and MCP client
# configuration for multi-mcp server.
# ============================================================================

# ----------------------------------------------------------------------------
# Constants and Configuration
# ----------------------------------------------------------------------------

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly VENV_PATH=".venv"
readonly ENV_FILE=".env"
readonly ENV_EXAMPLE=".env.example"
readonly REQUIRED_PYTHON_VERSION="3.13"

# ----------------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------------

print_success() {
    echo -e "${GREEN}✓${NC} $1" >&2
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1" >&2
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1" >&2
}

print_header() {
    echo "" >&2
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}" >&2
    echo -e "${BLUE}$1${NC}" >&2
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}" >&2
    echo "" >&2
}

get_script_dir() {
    cd "$(dirname "$0")/.." && pwd
}

# ----------------------------------------------------------------------------
# Validation Functions
# ----------------------------------------------------------------------------

check_uv_installed() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed"
        echo "" >&2
        echo "Please install uv first:" >&2
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
        echo "" >&2
        echo "Or visit: https://docs.astral.sh/uv/getting-started/installation/" >&2
        exit 1
    fi
    print_success "uv is installed"
}

check_python_version() {
    # Detect available Python command (python3 or python)
    local py_cmd="python3"
    if ! command -v python3 &>/dev/null; then
        if command -v python &>/dev/null; then
            py_cmd="python"
        else
            print_error "Python not found. Please install Python $REQUIRED_PYTHON_VERSION+"
            exit 1
        fi
    fi

    local python_version
    python_version=$($py_cmd --version 2>&1 | awk '{print $2}')

    # Use Python itself for version checking (portable across all platforms)
    if ! $py_cmd -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" 2>/dev/null; then
        print_warning "System Python $python_version found (Python $REQUIRED_PYTHON_VERSION+ recommended)"
        print_info "uv will manage Python versions automatically"
    else
        print_success "Python $python_version (meets requirement: $REQUIRED_PYTHON_VERSION+)"
    fi
}

# ----------------------------------------------------------------------------
# Installation Functions
# ----------------------------------------------------------------------------

create_venv() {
    print_info "Creating virtual environment..."

    if [[ -d "$VENV_PATH" ]]; then
        print_warning "Virtual environment already exists at $VENV_PATH"
        read -p "Remove and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_PATH"
            print_info "Removed existing venv"
        else
            print_info "Using existing venv"
            return 0
        fi
    fi

    uv venv "$VENV_PATH"
    print_success "Virtual environment created at $VENV_PATH"
}

install_dependencies() {
    print_info "Installing dependencies..."
    uv sync
    print_success "Dependencies installed"
}

setup_env_file() {
    print_info "Setting up environment configuration..."

    if [[ -f "$ENV_FILE" ]]; then
        print_warning "Found existing $ENV_FILE"
        read -p "Keep existing configuration? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_success "Keeping existing $ENV_FILE"
            return 0
        fi
    fi

    if [[ ! -f "$ENV_EXAMPLE" ]]; then
        print_error "Template file $ENV_EXAMPLE not found"
        exit 1
    fi

    cp "$ENV_EXAMPLE" "$ENV_FILE"
    print_success "Created $ENV_FILE from template"

    echo "" >&2
    print_warning "IMPORTANT: You must add your API keys to $ENV_FILE"
    print_info "Edit $ENV_FILE and add at least one API key:"
    echo "  - OPENAI_API_KEY=sk-..." >&2
    echo "  - ANTHROPIC_API_KEY=sk-ant-..." >&2
    echo "  - GEMINI_API_KEY=..." >&2
    echo "" >&2
}

get_claude_desktop_config_path() {
    # Detect Claude Desktop config path based on OS
    case "$(uname -s)" in
        Darwin*)
            echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
            ;;
        Linux*)
            echo "$HOME/.config/Claude/claude_desktop_config.json"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            # Windows: Convert Windows path to POSIX for filesystem operations
            local win_path="$APPDATA/Claude/claude_desktop_config.json"
            if command -v cygpath &>/dev/null; then
                cygpath -u "$win_path"
            else
                print_warning "cygpath not found; cannot locate Claude config on Windows"
                echo ""
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

get_claude_code_config_path() {
    # Claude Code config path (same on all platforms)
    echo "$HOME/.claude.json"
}

update_mcp_config_file() {
    local config_path="$1"
    local python_path="$2"
    local server_path="$3"
    local config_name="$4"  # "Claude Desktop" or "Claude Code"

    if [[ -z "$config_path" ]]; then
        print_warning "Could not detect $config_name config path for this OS"
        return 1
    fi

    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found - cannot automatically configure $config_name"
        print_info "Install jq with: brew install jq (macOS) or apt-get install jq (Linux)"
        return 1
    fi

    # Create config directory if it doesn't exist
    local config_dir
    config_dir=$(dirname "$config_path")
    if [[ ! -d "$config_dir" ]]; then
        print_info "Creating Claude config directory: $config_dir"
        if ! mkdir -p "$config_dir"; then
            print_error "Failed to create directory: $config_dir"
            return 1
        fi
    fi

    # Prepare for atomic config file update
    local temp_config
    temp_config=$(mktemp)
    # Cleanup temp file on function exit (use a subshell-safe approach)
    trap 'rm -f "$temp_config" 2>/dev/null || true; trap - RETURN' RETURN

    if [[ ! -f "$config_path" ]]; then
        # Create new config file using jq --arg for safe escaping
        print_info "Creating new $config_name config at $config_path"
        if ! echo '{"mcpServers": {}}' | jq --arg cmd "$python_path" --arg script "$server_path" \
            '.mcpServers.multi = {type: "stdio", command: $cmd, args: [$script]}' > "$temp_config"; then
            print_error "Failed to create $config_name config (jq error)"
            rm -f "$temp_config"
            return 1
        fi
        mv "$temp_config" "$config_path"
        rm -f "$temp_config" 2>/dev/null || true
        print_success "Added multi-mcp to $config_name config"
    else
        # Update existing config file
        print_info "Updating $config_name config at $config_path"

        # Check if multi server already exists
        if jq -e '.mcpServers.multi' "$config_path" &> /dev/null; then
            print_warning "Found existing 'multi' server in $config_name config"
            read -p "Overwrite existing configuration? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_info "Keeping existing configuration"
                return 0
            fi
        fi

        # Merge new config into existing file using jq --arg for safe escaping
        if ! jq --arg cmd "$python_path" --arg script "$server_path" \
            '.mcpServers.multi = {type: "stdio", command: $cmd, args: [$script]}' \
            "$config_path" > "$temp_config"; then
            print_error "Failed to update $config_name config (invalid JSON or jq error)"
            print_info "Your original config file has been preserved"
            rm -f "$temp_config"
            return 1
        fi
        mv "$temp_config" "$config_path"
        rm -f "$temp_config" 2>/dev/null || true
        print_success "Updated multi-mcp in $config_name config"
    fi

    print_success "MCP server configured at: $config_path"
}

add_mcp_config_to_claude() {
    local project_dir
    project_dir=$(get_script_dir)

    # Detect OS and set correct paths for virtual environment
    local venv_bin="bin"
    local python_exe="python"

    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*)
            # Windows: Use Scripts directory and python.exe
            venv_bin="Scripts"
            python_exe="python.exe"
            ;;
    esac

    local python_path="$project_dir/$VENV_PATH/$venv_bin/$python_exe"
    local server_path="$project_dir/src/server.py"

    # Convert to Windows native paths for Claude Desktop on Windows
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*)
            if command -v cygpath &>/dev/null; then
                python_path=$(cygpath -w "$python_path")
                server_path=$(cygpath -w "$server_path")
            fi
            ;;
    esac

    local success_count=0
    local desktop_config claude_code_config

    # Configure Claude Desktop
    desktop_config=$(get_claude_desktop_config_path)
    if [[ -n "$desktop_config" ]]; then
        echo "" >&2
        print_info "Configuring Claude Desktop..."
        if update_mcp_config_file "$desktop_config" "$python_path" "$server_path" "Claude Desktop"; then
            ((success_count++))
        fi
    fi

    # Configure Claude Code
    claude_code_config=$(get_claude_code_config_path)
    if [[ -n "$claude_code_config" ]]; then
        echo "" >&2
        print_info "Configuring Claude Code..."
        if update_mcp_config_file "$claude_code_config" "$python_path" "$server_path" "Claude Code"; then
            ((success_count++))
        fi
    fi

    if [[ $success_count -eq 0 ]]; then
        print_error "Failed to configure any MCP clients"
        return 1
    fi

    echo "" >&2
    print_warning "IMPORTANT: Restart Claude Desktop and/or Claude Code for changes to take effect"
    echo "" >&2
    return 0
}

generate_mcp_config() {
    local project_dir
    project_dir=$(get_script_dir)

    # Detect OS and set correct paths for virtual environment
    local venv_bin="bin"
    local python_exe="python"

    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*)
            # Windows: Use Scripts directory and python.exe
            venv_bin="Scripts"
            python_exe="python.exe"
            ;;
    esac

    local python_path="$project_dir/$VENV_PATH/$venv_bin/$python_exe"
    local server_path="$project_dir/src/server.py"

    # Convert to Windows native paths for Claude Desktop on Windows
    case "$(uname -s)" in
        CYGWIN*|MINGW*|MSYS*)
            if command -v cygpath &>/dev/null; then
                python_path=$(cygpath -w "$python_path")
                server_path=$(cygpath -w "$server_path")
            fi
            ;;
    esac

    print_header "MCP Client Configuration"

    # Try to automatically configure Claude Desktop
    echo "" >&2
    read -p "Automatically add to Claude Desktop config? (Y/n): " -n 1 -r
    echo
    echo "" >&2

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if add_mcp_config_to_claude; then
            return 0
        fi
        print_warning "Automatic configuration failed - showing manual instructions"
        echo "" >&2
    fi

    # Fallback: show manual instructions
    echo "Add this to your MCP client config:" >&2
    echo -e "${YELLOW}(~/.claude/settings.json or ~/Library/Application Support/Claude/claude_desktop_config.json)${NC}" >&2
    echo "" >&2
    cat <<EOF
{
  "mcpServers": {
    "multi": {
      "type": "stdio",
      "command": "$python_path",
      "args": [
        "$server_path"
      ]
    }
  }
}
EOF
    echo "" >&2
    print_info "After adding this configuration, restart your MCP client"
    print_info "Then type '/multi' to see available commands"
    echo "" >&2
}

test_installation() {
    print_header "Testing Installation"

    print_info "Verifying server can start..."

    # Test that server.py can be imported
    if "$VENV_PATH/bin/python" -c "import sys; sys.path.insert(0, '.'); from src.server import mcp" 2>/dev/null; then
        print_success "Server module loads correctly"
    else
        print_error "Server module failed to load"
        print_info "Try running: $VENV_PATH/bin/python src/server.py"
        return 1
    fi

    # Check if .env exists and has at least one API key
    if [[ -f "$ENV_FILE" ]]; then
        if grep -q "API_KEY=sk-\|API_KEY=.*[a-zA-Z0-9]" "$ENV_FILE"; then
            print_success "API keys configured in $ENV_FILE"
        else
            print_warning "No API keys found in $ENV_FILE"
            print_info "Add at least one API key before using the server"
        fi
    else
        print_warning "$ENV_FILE not found"
    fi

    echo "" >&2
    print_success "Installation test passed!"
    echo "" >&2
}

show_next_steps() {
    print_header "Next Steps"

    echo "1. ${GREEN}Add API Keys${NC}" >&2
    echo "   Edit $ENV_FILE and add your API keys" >&2
    echo "" >&2
    echo "2. ${GREEN}Configure MCP Client${NC}" >&2
    echo "   Add the configuration shown above to your MCP client" >&2
    echo "" >&2
    echo "3. ${GREEN}Restart MCP Client${NC}" >&2
    echo "   Restart Claude Desktop, Claude Code, or your MCP client" >&2
    echo "" >&2
    echo "4. ${GREEN}Verify Installation${NC}" >&2
    echo "   Type '/multi' in your MCP client to see available commands:" >&2
    echo "   - /multi:review   - Code review" >&2
    echo "   - /multi:chat     - AI chat" >&2
    echo "   - /multi:compare  - Model comparison" >&2
    echo "   - /multi:models   - List models" >&2
    echo "   - /multi:version  - Server info" >&2
    echo "" >&2
    echo "5. ${GREEN}Test a Command${NC}" >&2
    echo "   Try: /multi:models" >&2
    echo "" >&2

    print_info "For more information, see docs/install-v1.md"
    echo "" >&2
}

# ----------------------------------------------------------------------------
# Main Installation Flow
# ----------------------------------------------------------------------------

main() {
    local project_dir
    project_dir=$(get_script_dir)

    cd "$project_dir"

    print_header "Multi-MCP Installation"
    print_info "Installing to: $project_dir"
    echo "" >&2

    # Validation
    check_uv_installed
    check_python_version
    echo "" >&2

    # Installation
    create_venv
    install_dependencies
    setup_env_file

    # Configuration
    generate_mcp_config

    # Testing
    test_installation

    # Completion
    show_next_steps

    print_success "Installation complete!"
}

# Run main installation
main "$@"
