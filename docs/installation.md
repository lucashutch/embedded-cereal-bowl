# 💡 Installation Guide

Comprehensive installation instructions for Embedded Cereal Bowl tools.

## 🚀 Quick Installation

```bash
# Install from PyPI (recommended)
pip install embedded-cereal-bowl

# Install latest from GitHub
pip install git+https://github.com/lucashutch/embedded-cereal-bowl.git
```

## 📦 System Requirements

### Python Version
- **Minimum**: Python 3.12+
- **Recommended**: Latest Python 3.12+ release
- **Tested**: Python 3.12, 3.13, 3.14

### Operating Systems
- **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+
- **macOS**: 10.15+ (Catalina and newer)
- **Windows**: Windows 10+ with PowerShell or Git Bash

## 🔧 Installation Methods

### Method 1: PyPI Package (Recommended)
```bash
# Basic installation
pip install embedded-cereal-bowl

# Installation with user permissions
pip install --user embedded-cereal-bowl

# Upgrade existing installation
pip install --upgrade embedded-cereal-bowl
```

### Method 2: Development Installation
```bash
# Clone repository
git clone https://github.com/lucashutch/embedded-cereal-bowl.git
cd embedded-cereal-bowl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# Install in development mode
pip install -e ".[dev]"
```

### Method 3: Direct from Git
```bash
# Install latest main branch
pip install git+https://github.com/lucashutch/embedded-cereal-bowl.git@main

# Install specific version
pip install git+https://github.com/lucashutch/embedded-cereal-bowl.git@v0.1.0

# Install development version
pip install git+https://github.com/lucashutch/embedded-cereal-bowl.git@develop
```

### Method 4: From Source Archive
```bash
# Download and extract
wget https://github.com/lucashutch/embedded-cereal-bowl/archive/refs/tags/v0.1.0.tar.gz
tar -xzf v0.1.0.tar.gz
cd embedded-cereal-bowl-0.1.0

# Install from source
pip install .
```

## 🛠️ External Dependencies

### Required Runtime Dependencies
| Package | Version | Purpose | Installation |
|---|---|---|---|
| **pyserial** | >=3.5 | Serial communication | `pip install pyserial` |
| **regex** | >=2022.0.0 | Advanced regex | `pip install regex` |
| **colorama** | >=0.4.4 | Terminal colors | `pip install colorama` |

### Optional Development Dependencies
| Package | Version | Purpose | Installation |
|---|---|---|---|
| **pytest** | >=7.0 | Testing | `pip install pytest` |
| **pytest-mock** | >=3.10 | Test mocking | `pip install pytest-mock` |
| **pytest-cov** | >=4.0 | Coverage | `pip install pytest-cov` |
| **ruff** | >=0.1.0 | Linting/formatting | `pip install ruff` |
| **ty** | >=0.0.27 | Type checking | `pip install ty` |
| **bandit** | >=1.7 | Security scanning | `pip install bandit` |
| **build** | >=0.8.0 | Package building | `pip install build` |

### System Packages (Linux)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-dev python3-pip python3-venv

# For serial port access
sudo usermod -a -G dialout $USER

# For development tools
sudo apt install clang-format cmake-format
```

### System Packages (macOS)
```bash
# Homebrew (recommended)
brew install python3

# For development tools
brew install clang-format cmake-format

# For serial port access (if needed)
# macOS usually doesn't require special permissions
```

### System Packages (Windows)
```bash
# Using Chocolatey
choco install python

# Using Microsoft Store
# Install Python 3.12+ from Microsoft Store

# For development tools
choco install llvm cmake  # includes clang-format
```

## 🔍 Verification

### Check Installation
```bash
# Verify package installation
python -c "import embedded_cereal_bowl; print('Installation successful')"

# Check console script availability
monitor --help
timestamp --help
check-crlf --help
format-code --help
```

### Test Functionality
```bash
# Test timestamp conversion
timestamp "2025-01-21T14:10:34Z"

# Test line ending checker
check-crlf

# Test serial port detection (may need actual hardware)
monitor --help
```

### Development Environment Test
```bash
# Run test suite
uv run pytest --cov=src

# Run linting
uv run ruff check src tests

# Run type checking
uv run ty check

# Run security check
bandit -r src
```

## 🐛 Troubleshooting

### Permission Issues (Linux)
```bash
# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER

# Check current groups
groups $USER

# Log out and log in again for changes to take effect
```

### Virtual Environment Issues
```bash
# Create clean environment
python3 -m venv clean_venv
source clean_venv/bin/activate

# Verify Python version
python --version

# Clear pip cache if needed
pip cache purge
```

### Network Issues
```bash
# Use different PyPI mirror
pip install -i https://pypi.org/simple/ embedded-cereal-bowl



# Upgrade pip first
pip install --upgrade pip
```

### Platform-Specific Issues

#### Windows
```bash
# Use PowerShell instead of cmd
PowerShell

# Add Python to PATH (if not automatic)
$env:PATH += ";C:\\Python312\\Scripts;C:\\Python312"

# Use long path names if needed
pip install --embedded=c:\long\path\embedded-cereal-bowl
```

#### macOS
```bash
# Allow unsigned executables
xattr -d /path/to/executable

# Fix zsh completion issues
echo 'eval "$(python -m pip completion --zsh)"' >> ~/.zshrc
source ~/.zshrc
```

#### Linux
```bash
# Fix permissions for pip --user
export PATH="$HOME/.local/bin:$PATH"

# Handle system Python conflicts
alias python=python3
alias pip=pip3
```



## 📚 Alternative Installation Methods

### Using Conda
```bash
# Create conda environment
conda create -n embedded-tools python=3.12
conda activate embedded-tools

# Install from PyPI
pip install embedded-cereal-bowl
```

### Using Docker
```dockerfile
# Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install package
COPY . /app/
WORKDIR /app
RUN pip install -e .
```

### Using pipx (Isolated)
```bash
# Install pipx
pip install pipx

# Install tool in isolation
pipx install embedded-cereal-bowl
```

## 🔄 Upgrades and Maintenance

### Upgrade Package
```bash
# Upgrade to latest version
pip install --upgrade embedded-cereal-bowl

# Check for outdated packages
pip list --outdated

# Upgrade specific dependencies
pip install --upgrade pyserial regex colorama
```

### Uninstall
```bash
# Remove package
pip uninstall embedded-cereal-bowl

# Remove development dependencies
pip uninstall pytest ruff ty bandit
```

### Clean Installation
```bash
# Remove virtual environment
deactivate
rm -rf venv/

# Remove pip cache and build artifacts
pip cache purge
rm -rf build/ dist/ *.egg-info/
```

## 🎯 Next Steps

After installation:

1. **For immediate usage**: See [Main README](../README.md)
2. **For detailed tool guides**: Browse [Tool Documentation](.)
3. **For development**: See [Contributing Guide](../CONTRIBUTING.md)
4. **For examples**: See [Examples Directory](examples/)

## 📞 Support

If you encounter installation issues:

1. Check [Troubleshooting Guide](examples/troubleshooting.md)
2. Search [GitHub Issues](https://github.com/lucashutch/embedded-cereal-bowl/issues)
3. Create a new issue with:
   - Operating system and version
   - Python version (`python --version`)
   - Installation method used
   - Complete error message