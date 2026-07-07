.PHONY: setup

setup:
	@echo "Setting up git hooks..."
	@git config core.hooksPath .githooks
	@echo "Done. git hooks are configured."
