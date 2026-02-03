#!/bin/bash

# Unified Lint Suite for Terraform Stacks
#
# This script runs a comprehensive, multi-layered linting suite to ensure code quality,
# prevent configuration drift, and catch subtle "missing wiring" bugs.
#
# Usage: ./scripts/run_lint_suite.sh [TARGET_DIR]
# Defaults to current directory if TARGET_DIR is not provided.
#
# --------------------------------------------------------------------------------
# LINTING STRATEGY & DOCUMENTATION
# --------------------------------------------------------------------------------
#
# ## Tools & Layers
#
# 1. Terraform Validate
#    - Command: `terraform validate`
#    - Purpose: Ensures the configuration is syntactically valid and internally consistent.
#    - Catches: Syntax errors, missing required module inputs, type mismatches.
#
# 2. TFLint
#    - Command: `tflint`
#    - Purpose: Advanced static analysis and best practices.
#    - Configuration: Rules are defined in `.tflint.hcl` at the repository root.
#    - Key Checks:
#      - Unused Declarations: Variables or data sources defined but never referenced.
#      - Google Provider Rules: Validates machine types, regions, and IAM members.
#      - Deep Checking: Verifies if Google Cloud APIs are actually enabled (in CI).
#
# 3. Variable Wiring Check (Custom)
#    - Command: `python3 scripts/check_variable_wiring.py`
#    - Purpose: Detects "Partial Usage" bugs in complex object variables (specifically `cloud_run`).
#    - The Problem: Standard linters consider a variable "used" if you simply loop over it.
#      They FAIL to detect if you defined a specific field (like `datadog_service_name`)
#      in the variable structure but forgot to map it to the module input.
#    - How it Works:
#      - Parses `variables.tf` (using `python-hcl2`) to determine the contract.
#      - Parses module calls (using `terraform-config-inspect`) to determine implementation.
#      - Fails if a key is part of the contract but ignored in the implementation.
#
# ## Continuous Integration
#
# These checks are enforced in the GitHub Actions pipeline (`Reusable Terraform Plan`).
# Failures are reported as GitHub Annotations in Pull Requests.
#
# ## Troubleshooting
#
# ### Error: `variable "xyz" is declared but not used` (TFLint)
#    - Cause: Variable defined in `variables.tf` but not referenced in `.tf` files.
#    - Fix: Delete the variable if dead, or wire it up if needed.
#
# ### Error: `Missing wiring for 'cloud_run' keys: datadog_service_name` (Wiring Check)
#    - Cause: Field defined in `cloud_run` variable object but passed to module.
#    - Fix: Map the attribute in the `cloud_run_v2` module block in `cloud_run.tf`:
#      `datadog_service_name = each.value.datadog_service_name`
#
# ### Error: `Plugin "google" not found`
#    - Cause: TFLint plugins not installed locally.
#    - Fix: Run `tflint --init` (referencing config).
#
# ## Prerequisites for Local Development
# 1. Terraform
# 2. TFLint (`brew install tflint`)
# 3. Python 3 + `python-hcl2` (`pip install python-hcl2`)
# 4. terraform-config-inspect (`go install github.com/hashicorp/terraform-config-inspect@latest`)
# --------------------------------------------------------------------------------

set -o pipefail

TARGET_DIR="${1:-.}"
ABS_TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "Linting Stack: $TARGET_DIR"
echo "=================================================="

FAILURE=0

# Ensure we are in the target directory for context-sensitive tools
cd "$ABS_TARGET_DIR" || exit 1

# --------------------------------------------------------
# 1. Terraform Validate
# --------------------------------------------------------
echo "--> [1/3] terraform validate"

# Check if terraform is initialized (hidden .terraform dir exists)
# If not, try a backend-less init to allow validation
if [ ! -d ".terraform" ]; then
    echo "    ⚠️  .terraform directory not found. Running 'terraform init -backend=false'..."
    if ! terraform init -backend=false -input=false > /dev/null; then
        echo "    ❌ Init failed"
        FAILURE=1
    fi
fi

if [ "$FAILURE" -eq 0 ]; then
    if ! terraform validate -no-color; then
        echo "    ❌ FAILED"
        FAILURE=1
    else
        echo "    ✅ PASSED"
    fi
else
    echo "    ⚠️  Skipping validate due to init failure"
fi

# --------------------------------------------------------
# 2. TFLint
# --------------------------------------------------------
echo "--> [2/3] tflint"
TFLINT_CONFIG="$REPO_ROOT/.tflint.hcl"

if ! command -v tflint &> /dev/null; then
    echo "    ⚠️  tflint not found. Skipping."
else
    # We assume tflint --init has been run or plugins are cached in CI/local env
    if ! tflint --config="$TFLINT_CONFIG" --format=compact; then
        echo "    ❌ FAILED"
        FAILURE=1
    else
        echo "    ✅ PASSED"
    fi
fi

# --------------------------------------------------------
# 3. Check Variable Wiring
# --------------------------------------------------------
echo "--> [3/3] check_variable_wiring.py"
WIRING_SCRIPT="$SCRIPT_DIR/check_variable_wiring.py"

# Use uv if available for robust dependency handling, otherwise fallback to system python
if command -v uv &> /dev/null; then
    # uv run handles ephemeral venv and dependency installation (python-hcl2)
    CMD="uv run --with python-hcl2 $WIRING_SCRIPT $ABS_TARGET_DIR"
else
    CMD="python3 $WIRING_SCRIPT $ABS_TARGET_DIR"
fi

if ! $CMD; then
    echo "    ❌ FAILED"
    FAILURE=1
else
    echo "    ✅ PASSED"
fi

echo "=================================================="
if [ "$FAILURE" -ne 0 ]; then
    echo "🚨 LINTING FAILED for $TARGET_DIR"
    exit 1
else
    echo "✨ ALL CHECKS PASSED for $TARGET_DIR"
    exit 0
fi