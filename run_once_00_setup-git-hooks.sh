#!/bin/bash
# Set up git hooks for credential scanning
chezmoi cd
git config core.hooksPath .githooks
echo "✅ git hooks configured (core.hooksPath = .githooks)"
