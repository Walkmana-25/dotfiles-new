#!/bin/bash
# Set up git hooks for credential scanning
cd "${CHEZMOI_SOURCE_DIR}" || exit 1
git config core.hooksPath .githooks
echo "✅ git hooks configured (core.hooksPath = .githooks)"
