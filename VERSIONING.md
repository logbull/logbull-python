# Automatic Versioning with Custom Commit Format

This project uses **python-semantic-release** to automatically manage versions, generate changelogs, and publish releases based on your custom commit message format.

## 🎯 Commit Format

### Required Format

```
<TYPE> (area): What was done
```

### Supported Types

| Commit Type                    | Version Bump              | Description                          | Example                                                  |
| ------------------------------ | ------------------------- | ------------------------------------ | -------------------------------------------------------- |
| `FEATURE (area): description`  | **MINOR** (0.1.0 → 0.2.0) | New features and enhancements        | `FEATURE (logger): add context support to logger`        |
| `FIX (area): description`      | **PATCH** (0.1.0 → 0.1.1) | Bug fixes and patches                | `FIX (connection): resolve timeout issue in HTTP client` |
| `REFACTOR (area): description` | **No bump**               | Code refactoring (no version change) | `REFACTOR (handlers): reorganize handler structure`      |

### Examples from Your Guidelines

```bash
# Feature additions (minor version bump)
git commit -m "FEATURE (kubernetes): add support for Helm deployments"
git commit -m "FEATURE (auth): implement JWT token validation"
git commit -m "FEATURE (logging): add structured logging with fields"

# Bug fixes (patch version bump)
git commit -m "FIX (healthcheck): make health endpoint optional"
git commit -m "FIX (config): handle missing configuration files gracefully"
git commit -m "FIX (sender): prevent memory leak in batch processor"

# Refactoring (no version bump)
git commit -m "REFACTOR (navbar): reorganize navigation component structure"
git commit -m "REFACTOR (utils): extract common validation logic"
git commit -m "REFACTOR (tests): consolidate test helper functions"
```

## 🚀 Branch Naming Convention

Follow your established branch naming pattern:

```bash
# Feature branches
feature/add_support_of_kubernetes_helm
feature/implement_jwt_validation
feature/add_structured_logging

# Bug fix branches
fix/make_healthcheck_optional
fix/handle_missing_config_files
fix/prevent_memory_leak

# Refactoring branches
refactor/refactor_navbar
refactor/extract_validation_logic
refactor/consolidate_test_helpers
```

## ⚡ Automatic Release Process

### When Releases Happen

1. **On every push to `main/master` branch**
2. **Only for `FEATURE` and `FIX` commits** (REFACTOR doesn't trigger releases)
3. **After all tests pass**

### What Happens Automatically

When you push commits with proper format:

```bash
git push origin main
```

The system automatically:

1. **Analyzes commits** since last release
2. **Determines version bump**:
   - `FEATURE` commits → **minor** version bump
   - `FIX` commits → **patch** version bump
   - `REFACTOR` commits → no version bump
3. **Updates version** in:
   - `pyproject.toml`
   - `logbull/__init__.py`
4. **Generates CHANGELOG.md** with grouped changes
5. **Creates git tag** (e.g., `v0.2.0`)
6. **Builds package** using `uv build`
7. **Publishes to PyPI** (requires `PYPI_API_TOKEN` secret)
8. **Creates GitHub release** with changelog
