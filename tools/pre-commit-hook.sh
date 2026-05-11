#!/bin/bash
# Pre-commit hook: Python syntax + API import check
# Prevents IndentationError/SyntaxError from reaching Railway.
# Install: ./tools/install-hooks.sh

echo "Running Python syntax check..."

FAILED=0

for file in $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$'); do
    if [ -f "$file" ]; then
        python3 -m py_compile "$file" 2>&1
        if [ $? -ne 0 ]; then
            echo "SYNTAX ERROR in: $file"
            FAILED=1
        fi
    fi
done

if [ $FAILED -eq 1 ]; then
    echo ""
    echo "================================================================="
    echo "  COMMIT BLOCKED -- Python syntax errors found"
    echo "  Fix all errors above and run git commit again."
    echo "================================================================="
    exit 1
fi

if git diff --cached --name-only | grep -q '\.py$'; then
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from src.api.app import app
    print('API import check passed')
except Exception as e:
    print(f'API import failed: {e}')
    sys.exit(1)
" 2>&1
    if [ $? -ne 0 ]; then
        echo ""
        echo "================================================================="
        echo "  COMMIT BLOCKED -- API import check failed"
        echo "  The full API could not be imported. Fix before committing."
        echo "================================================================="
        exit 1
    fi
fi

if git diff --cached --name-only | grep -q '^frontend/src/'; then
    echo "Running frontend type check..."
    cd frontend && npx tsc --noEmit 2>&1
    if [ $? -ne 0 ]; then
        echo ""
        echo "================================================================="
        echo "  COMMIT BLOCKED -- TypeScript errors found in frontend"
        echo "  Fix all type errors above and run git commit again."
        echo "================================================================="
        exit 1
    fi
    cd ..
    echo "Frontend type check passed"
fi

echo "All pre-commit checks passed"
exit 0
