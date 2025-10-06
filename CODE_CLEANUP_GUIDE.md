# Code Cleanup Guide (T165)

This guide provides instructions for final code cleanup, linting, and quality checks.

## Overview

T165 involves:
1. Removing TODO comments and placeholder code
2. Fixing linting errors (backend and frontend)
3. Formatting code consistently
4. Updating CHANGELOG.md (✅ Already completed)
5. Final quality checks

## Prerequisites

- All tests passing (T164 completed)
- Development environment set up
- Git working directory clean (commit current work)

## Backend Cleanup

### 1. Remove TODOs and Placeholders

Search for TODO comments and address them:

```bash
cd backend

# Find all TODO comments
grep -r "TODO" src/ --include="*.py" | grep -v "__pycache__"

# Find FIXME comments
grep -r "FIXME" src/ --include="*.py" | grep -v "__pycache__"

# Find XXX comments
grep -r "XXX" src/ --include="*.py" | grep -v "__pycache__"

# Find placeholder code
grep -r "pass  # placeholder" src/ --include="*.py"
grep -r "raise NotImplementedError" src/ --include="*.py"
```

**Action items**:
- Replace TODO comments with actual implementation or remove if completed
- Remove or complete FIXME sections
- Replace `pass` with actual logic or proper comments
- Remove `NotImplementedError` if implemented

### 2. Run Linting (flake8)

Check code quality with flake8:

```bash
cd backend
source venv/bin/activate

# Run flake8 on source code
flake8 src/ --count --show-source --statistics

# Run flake8 on tests
flake8 tests/ --count --show-source --statistics

# Common issues to fix:
# E501: line too long (>127 characters) - break into multiple lines
# F401: imported but unused - remove unused imports
# E302: expected 2 blank lines - add blank lines between functions
# E305: expected 2 blank lines after class - add blank lines
# W291: trailing whitespace - remove trailing spaces
```

**Configuration** (already in `backend/.flake8` or `backend/setup.cfg`):
```ini
[flake8]
max-line-length = 127
exclude = __pycache__,.venv,venv,alembic/versions
ignore = E203,W503
```

### 3. Run Type Checking (mypy)

Verify type annotations:

```bash
cd backend
source venv/bin/activate

# Run mypy
mypy src/ --ignore-missing-imports --show-error-codes

# Common issues to fix:
# error: Function is missing a return type annotation
# error: Argument has incompatible type
# error: Item "None" of "Optional[X]" has no attribute "Y"
```

**Configuration** (already in `backend/pyproject.toml` or `backend/mypy.ini`):
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
ignore_missing_imports = True
```

### 4. Format Code (black)

Auto-format all Python code:

```bash
cd backend
source venv/bin/activate

# Check what would be changed (dry run)
black --check src/ tests/

# Format all code
black src/ tests/

# Output:
# reformatted X files
# Y files left unchanged
```

**Configuration** (already in `backend/pyproject.toml`):
```toml
[tool.black]
line-length = 127
target-version = ['py311']
include = '\.pyi?$'
```

### 5. Sort Imports (isort)

Organize import statements:

```bash
cd backend
source venv/bin/activate

# Check import order (dry run)
isort --check-only src/ tests/

# Sort imports
isort src/ tests/

# Output:
# Fixing X files
```

**Configuration** (already in `backend/pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 127
```

### 6. Security Check (bandit)

Scan for security issues:

```bash
cd backend
source venv/bin/activate

# Run security scan
bandit -r src/ -f json -o bandit-report.json

# View report
cat bandit-report.json | jq '.results'

# Common issues to fix:
# B608: Possible SQL injection - use parameterized queries
# B105: Possible hardcoded password - use environment variables
# B201: Flask app with debug=True - ensure debug=False in production
```

### 7. Remove Unused Code

Identify and remove dead code:

```bash
cd backend
source venv/bin/activate

# Install vulture if not present
pip install vulture

# Find unused code
vulture src/ --min-confidence 80

# Review output and remove confirmed unused:
# - Unused functions
# - Unused variables
# - Unused imports (already caught by flake8)
```

## Frontend Cleanup

### 1. Remove TODOs and Placeholders

Search for TODO comments:

```bash
cd frontend

# Find all TODO comments
grep -r "TODO" src/ --include="*.ts" --include="*.tsx"

# Find FIXME comments
grep -r "FIXME" src/ --include="*.ts" --include="*.tsx"

# Find console.log statements (remove or convert to proper logging)
grep -r "console.log" src/ --include="*.ts" --include="*.tsx"
```

**Action items**:
- Replace TODO with implementation or remove if completed
- Remove console.log or replace with proper logging
- Remove commented-out code blocks

### 2. Run Linting (ESLint)

Check code quality:

```bash
cd frontend

# Run ESLint
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix

# Common issues to fix:
# '@typescript-eslint/no-unused-vars' - remove unused variables
# '@typescript-eslint/no-explicit-any' - replace 'any' with proper types
# 'react-hooks/exhaustive-deps' - add missing dependencies to useEffect
# 'react/jsx-key' - add key prop to mapped elements
```

**Configuration** (already in `frontend/.eslintrc.json`):
```json
{
  "extends": ["next/core-web-vitals", "prettier"],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

### 3. Run Type Checking (TypeScript)

Verify types:

```bash
cd frontend

# Run TypeScript compiler in check mode
npm run type-check

# Or: npx tsc --noEmit

# Common issues to fix:
# TS2322: Type 'X' is not assignable to type 'Y'
# TS2345: Argument of type 'X' is not assignable to parameter of type 'Y'
# TS2339: Property 'X' does not exist on type 'Y'
# TS18048: 'X' is possibly 'undefined'
```

### 4. Format Code (Prettier)

Auto-format all code:

```bash
cd frontend

# Check formatting (dry run)
npm run format:check

# Format all code
npm run format

# Or: npx prettier --write "src/**/*.{ts,tsx,js,jsx,json,css,md}"
```

**Configuration** (already in `frontend/.prettierrc`):
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "tabWidth": 2,
  "printWidth": 100
}
```

### 5. Check Bundle Size

Analyze and optimize bundle:

```bash
cd frontend

# Build with bundle analyzer
npm run build

# Check bundle size
du -sh .next/

# Review .next/static/ for large chunks
ls -lh .next/static/chunks/

# If bundle is too large:
# - Enable tree shaking
# - Lazy load components
# - Code split with dynamic imports
# - Optimize images
```

### 6. Remove Unused Dependencies

Check for unused packages:

```bash
cd frontend

# Install depcheck if needed
npm install -g depcheck

# Run depcheck
depcheck

# Review output:
# - Unused dependencies - remove from package.json
# - Missing dependencies - add to package.json

# Remove unused packages
npm uninstall <package-name>
```

### 7. Accessibility Check

Ensure WCAG compliance:

```bash
cd frontend

# Install axe-core if not present
npm install -D @axe-core/react

# Add to _app.tsx for development:
if (process.env.NODE_ENV !== 'production') {
  const axe = require('@axe-core/react');
  axe(React, ReactDOM, 1000);
}

# Run build and check console for accessibility warnings
npm run build
npm run start
# Open browser console and check for axe violations
```

## Documentation Cleanup

### 1. Update README.md

Ensure README is complete and accurate:

```bash
# Review README.md
cat README.md

# Should include:
# - Project description
# - Features
# - Tech stack
# - Quick start guide
# - Links to detailed docs
# - Contributing guidelines
# - License information
```

### 2. Review Documentation Links

Check that all documentation links work:

```bash
# Find all markdown links
grep -r "\[.*\](.*\.md)" docs/ README.md

# Verify each linked file exists
# Fix broken links
```

### 3. Update API Documentation

Ensure OpenAPI spec is current:

```bash
# Generate OpenAPI spec from running backend
cd backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Fetch OpenAPI JSON
curl http://localhost:8000/openapi.json > openapi_generated.json

# Compare with contracts/openapi.yaml
# Update if there are discrepancies

# Stop backend
pkill uvicorn
```

## Git Cleanup

### 1. Remove Untracked Files

Clean up development artifacts:

```bash
# Preview what would be removed
git clean -n -d

# Remove untracked files and directories
git clean -f -d

# Remove ignored files (be careful!)
git clean -f -d -x
```

### 2. Review .gitignore

Ensure all build artifacts are ignored:

```bash
# Check .gitignore is comprehensive
cat .gitignore

# Should ignore:
# - __pycache__/
# - *.pyc
# - .pytest_cache/
# - htmlcov/
# - .coverage
# - node_modules/
# - .next/
# - *.log
# - .env (but not .env.example)
# - venv/
```

### 3. Check for Committed Secrets

Scan for accidentally committed secrets:

```bash
# Install gitleaks if not present
brew install gitleaks

# Scan repository
gitleaks detect --source . --verbose

# If secrets found:
# 1. Remove from history (git filter-repo)
# 2. Rotate the compromised secrets
# 3. Update .gitignore to prevent recurrence
```

## Final Validation

### 1. Run All Quality Checks

Backend:
```bash
cd backend
source venv/bin/activate

# All checks in sequence
black --check src/ tests/ && \
isort --check-only src/ tests/ && \
flake8 src/ tests/ && \
mypy src/ --ignore-missing-imports && \
bandit -r src/ -f json && \
pytest tests/ --cov=src --cov-report=term

# Expected: All checks pass ✅
```

Frontend:
```bash
cd frontend

# All checks in sequence
npm run type-check && \
npm run lint && \
npm run format:check && \
npm test -- --coverage --watchAll=false && \
npm run build

# Expected: All checks pass ✅
```

### 2. Create Pre-commit Hook (Optional)

Automate quality checks:

```bash
# Create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

echo "Running pre-commit checks..."

# Backend checks
cd backend
source venv/bin/activate
black --check src/ tests/ || exit 1
isort --check-only src/ tests/ || exit 1
flake8 src/ tests/ || exit 1

# Frontend checks
cd ../frontend
npm run lint || exit 1
npm run type-check || exit 1

echo "✅ All pre-commit checks passed"
EOF

chmod +x .git/hooks/pre-commit
```

### 3. Update Project Status

Mark tasks as complete:

```bash
# Update tasks.md
# Change T164 and T165 from [ ] to [x]

# Update CHANGELOG.md (already done ✅)

# Create completion summary
echo "## Phase 3.5 Complete" >> PROJECT_STATUS.md
echo "- All 165 tasks completed ✅" >> PROJECT_STATUS.md
echo "- Test coverage: 85%+ backend, 80%+ frontend" >> PROJECT_STATUS.md
echo "- Code quality: All linting and type checks pass" >> PROJECT_STATUS.md
echo "- Documentation: Complete (7 guides, 9,000+ lines)" >> PROJECT_STATUS.md
```

## Checklist

**Backend Cleanup**:
- [ ] All TODOs addressed or removed
- [ ] flake8 passes with no errors
- [ ] mypy passes with no errors
- [ ] black formatting applied
- [ ] isort applied
- [ ] bandit security scan reviewed
- [ ] No unused code (vulture)
- [ ] Tests pass (pytest)

**Frontend Cleanup**:
- [ ] All TODOs addressed or removed
- [ ] ESLint passes with no errors
- [ ] TypeScript compilation succeeds
- [ ] Prettier formatting applied
- [ ] No console.log statements
- [ ] Bundle size acceptable
- [ ] No unused dependencies
- [ ] Tests pass (Jest + Playwright)

**Documentation**:
- [ ] README.md complete and accurate
- [ ] All doc links work
- [ ] API documentation current
- [ ] CHANGELOG.md updated ✅

**Repository**:
- [ ] .gitignore comprehensive
- [ ] No committed secrets
- [ ] No untracked artifacts
- [ ] Git history clean

**Final Validation**:
- [ ] All quality checks pass
- [ ] Pre-commit hooks installed (optional)
- [ ] Tasks.md updated
- [ ] Project status documented

## Common Issues and Solutions

### Issue: Black and flake8 Conflict

**Problem**: Black formats to 88 chars, flake8 complains about 80

**Solution**: Configure flake8 to match black:
```ini
[flake8]
max-line-length = 127
extend-ignore = E203,W503
```

### Issue: isort and Black Conflict

**Problem**: Import formatting conflicts

**Solution**: Use isort's black profile:
```toml
[tool.isort]
profile = "black"
```

### Issue: Many Type Errors

**Problem**: Hundreds of mypy errors

**Solution**: Start with `--ignore-missing-imports`, fix gradually:
```bash
# Ignore missing imports initially
mypy src/ --ignore-missing-imports

# Then fix specific modules
mypy src/services/auth_service.py --strict
```

### Issue: Large Bundle Size

**Problem**: Frontend bundle > 500KB

**Solution**:
```typescript
// Use dynamic imports
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <LoadingSpinner />
});

// Enable tree shaking in next.config.js
module.exports = {
  webpack: (config) => {
    config.optimization.usedExports = true;
    return config;
  }
};
```

## Automation

### CI/CD Integration

Quality checks are automated in `.github/workflows/`:

- **backend-ci.yml**: Runs linting, type checking, tests on every push
- **frontend-ci.yml**: Runs ESLint, TypeScript, tests on every push
- **Pull requests**: Must pass all checks before merge

### Git Hooks

Install automated checks:
```bash
# Using pre-commit framework
pip install pre-commit
pre-commit install

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
EOF
```

## Next Steps

After completing code cleanup:

1. ✅ Mark T165 as complete in tasks.md
2. → Commit all cleanup changes
3. → Create final release tag (v0.1.0)
4. → Deploy to staging environment
5. → Begin user acceptance testing

---

**Code Cleanup Complete When**:
- All automated checks pass ✅
- No TODO/FIXME comments remain
- Documentation is current
- Git repository is clean
- Tests pass with good coverage
- Ready for production deployment
