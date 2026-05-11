#!/bin/bash
# Run once after cloning: ./tools/install-hooks.sh
cp tools/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "Git hooks installed."
echo "  Python syntax + TS type checks will run on every commit."
