#!/bin/bash
# Set up git hooks for credential scanning
cd "$(chezmoi source-path)" || exit
git config core.hooksPath .githooks
echo "✅ git hooks configured (core.hooksPath = .githooks)"
