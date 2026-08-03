#!/usr/bin/env bash
# Rebuild backend artifacts from the live Watchfloor UI (source of truth).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

echo "==> Sync registry from ui/watchfloor.html"
node scripts/sync_registry_from_ui.js

echo "==> Export Watchfloor contracts"
agent-fleet export-contracts --watchfloor

echo "==> Generate 25-layer blueprints"
agent-fleet blueprints

echo "==> Refresh Institutional Design Council plan"
agent-fleet enhance

echo "==> Publish UI data copies (served from ui/)"
mkdir -p ui/data
python3 - <<'PY'
import json
from pathlib import Path

root = Path(".")
reg = json.loads((root / "config/watchfloor_registry.json").read_text())
bp = json.loads((root / "docs/agent_blueprints/blueprints.json").read_text())
contracts = json.loads((root / "docs/agent_contracts/watchfloor_contracts.json").read_text())

ui = root / "ui/data"
ui.mkdir(parents=True, exist_ok=True)

# Stable ASCII-escaped JSON for portable diffs / fetch from http.server
(ui / "watchfloor_registry.json").write_text(
    json.dumps(reg, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
)
(ui / "blueprints.json").write_text(
    json.dumps(bp, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
)
(ui / "watchfloor_contracts.json").write_text(
    json.dumps(contracts, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
)

# Also normalize canonical registry for consistent unicode escapes
(root / "config/watchfloor_registry.json").write_text(
    json.dumps(reg, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
)

meta = {
    "source": "ui/watchfloor.html",
    "registry_version": reg.get("version"),
    "rebuilt_at": reg.get("rebuilt_at"),
    "counts": reg.get("counts"),
    "blueprint_agents": len(bp),
    "contract_agents": len(contracts),
    "layers": 25,
}
(ui / "rebuild_meta.json").write_text(
    json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
)
print(json.dumps(meta, indent=2))
PY

echo "==> Done. Serve with: cd ui && python3 -m http.server 8765 --bind 127.0.0.1"
