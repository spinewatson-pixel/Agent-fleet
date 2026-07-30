#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m agent_fleet.cli paper-run --symbol "${1:-AAPL}" --price "${2:-190}" --strategy "${3:-STRAT-MOM-001}"
