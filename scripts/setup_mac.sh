#!/bin/bash

echo "--------------------------------------------------"
echo "Setup Script For Darwin Based System"
echo "--------------------------------------------------"


if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Install Homebrew"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi


echo "--------------------------------------------------"
echo "Install Brew Application"
echo "--------------------------------------------------"
brew update

PACKAGES=(
    git
    jq
    wget
    tmux
    gh
)

for pkg in "${PACKAGES[@]}"; do
    if brew list "$pkg" &> /dev/null; then
        echo "${pkg} is already installed."
    else
        echo "${pkg} is not installed. Installing..."
        brew install "$pkg"
    fi
done

echo "--------------------------------------------------"
echo "Install Brew Cask Application"
echo "--------------------------------------------------"

PACKAGES_CASK=(
)

for pkg in "${PACKAGES_CASK[@]}"; do
    if brew list "$pkg" &> /dev/null; then
        echo "${pkg} is already installed."
    else
        echo "${pkg} is not installed. Installing..."
        brew install --cask "$pkg"
    fi
done