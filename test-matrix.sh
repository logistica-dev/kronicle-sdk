#!/usr/bin/env bash
# Local pre-push entrypoint. Runs the exact same tox environments as CI
# (see [tool.tox] in pyproject.toml) — no commands are duplicated here.
#
#   ./test-matrix.sh              # all Python versions + quality
#   ./test-matrix.sh -e py312     # a single environment
set -euo pipefail
cd "$(dirname "$0")"
exec uv run --locked tox "$@"
