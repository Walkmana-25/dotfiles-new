#!/bin/bash
# Set up git hooks for credential scanning
git config core.hooksPath .githooks
echo "✅ git hooks configured (core.hooksPath = .githooks)"
