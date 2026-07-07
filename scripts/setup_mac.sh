#!/bin/bash

echo "Setup Script For Darwin Based System"


if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install Homebrew"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

