#!/bin/zsh
set -e

PROJECT_NAME="nytc"
PROJECT_DIR="$HOME/Desktop/$PROJECT_NAME"
VENV_NAME="venv"

echo "Checking for Homebrew..."

# Install Homebrew if not installed
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon or Intel
    if [[ -d "/opt/homebrew/bin" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "Homebrew already installed."
fi

echo "Updating Homebrew..."
brew update

echo "Installing Python 3.13..."
brew install python@3.13

PYTHON_BIN=$(brew --prefix python@3.13)/bin/python3.13

echo "Creating project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "Creating requirements.txt..."

cat <<EOF > requirements.txt
ugot
opencv-python
ipykernel
ipython
ultralytics
EOF

echo "Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_NAME"

echo "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo "-----------------------------------------------"
echo ""
echo "Setup complete!"
echo "Project created at: $PROJECT_DIR"
echo ""