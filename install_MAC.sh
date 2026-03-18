#!/bin/zsh
set -e

PROJECT_PARENT="$HOME/Desktop"
REPO_URL="https://github.com/teacher-tta/National-Youth-Tech-Championship-2026"
REPO_NAME="National-Youth-Tech-Championship-2026"
VENV_NAME="venv"

echo "Checking for Homebrew..."

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

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

echo "Installing dependencies (python)..."
brew install python@3.13

PYTHON_BIN=$(brew --prefix python@3.13)/bin/python3.13

echo "Moving to Desktop..."
cd "$PROJECT_PARENT"

echo "Downloading repository as ZIP..."
if [ ! -d "$REPO_NAME" ]; then
    curl -L "$REPO_URL/archive/refs/heads/main.zip" -o "$REPO_NAME.zip"
    unzip "$REPO_NAME.zip"
    mv "$REPO_NAME-main" "$REPO_NAME"
    rm "$REPO_NAME.zip"
else
    echo "Repository folder already exists. Skipping download."
fi

echo "Entering repository folder..."
cd "$REPO_NAME"

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
echo "Project located at:"
echo "$PROJECT_PARENT/$REPO_NAME"
echo ""
