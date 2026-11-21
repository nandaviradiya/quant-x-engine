#!/usr/bin/env bash
# ============================================================
# deploy-to-hf.sh  —  Push QUANT-X backend to Hugging Face Spaces
# Usage:  bash deploy-to-hf.sh <HF_USERNAME> <HF_TOKEN>
# ============================================================
set -e

HF_USERNAME="${1}"
HF_TOKEN="${2}"
SPACE_NAME="quant-x-engine"
REPO_ID="${HF_USERNAME}/${SPACE_NAME}"
HF_SPACE_DIR="/tmp/hf-quant-x-space"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "$HF_USERNAME" || -z "$HF_TOKEN" ]]; then
  echo "Usage: bash deploy-to-hf.sh <HF_USERNAME> <HF_TOKEN>"
  exit 1
fi

echo ""
echo "============================================================"
echo "  QUANT-X  →  Hugging Face Spaces Deployment"
echo "  Space: https://huggingface.co/spaces/${REPO_ID}"
echo "============================================================"
echo ""

# ── 1. Install huggingface_hub CLI ───────────────────────────────────────────
echo "[1/6] Installing huggingface_hub CLI..."
pip install -q "huggingface_hub[cli]>=0.23.0"

# ── 2. Create the Space (idempotent) ─────────────────────────────────────────
echo "[2/6] Creating Hugging Face Space (if not exists)..."
python3 - <<PYEOF
from huggingface_hub import HfApi
api = HfApi(token="${HF_TOKEN}")
try:
    api.create_repo(
        repo_id="${REPO_ID}",
        repo_type="space",
        space_sdk="docker",
        private=False,
        exist_ok=True,
    )
    print("  Space ready: https://huggingface.co/spaces/${REPO_ID}")
except Exception as e:
    print(f"  Warning: {e}")
PYEOF

# ── 3. Clone the Space repo ───────────────────────────────────────────────────
echo "[3/6] Cloning HF Space repo..."
rm -rf "${HF_SPACE_DIR}"
git clone "https://user:${HF_TOKEN}@huggingface.co/spaces/${REPO_ID}" "${HF_SPACE_DIR}"

# Configure git identity inside the clone
cd "${HF_SPACE_DIR}"
git config user.email "quant-x@deploy.local"
git config user.name "QUANT-X Deploy"

# ── 4. Copy deployment files ──────────────────────────────────────────────────
echo "[4/6] Copying deployment files..."
# Clean everything except .git
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

cp "${SCRIPT_DIR}/Dockerfile"      .
cp "${SCRIPT_DIR}/requirements.txt" .
cp "${SCRIPT_DIR}/README.md"        .
cp "${SCRIPT_DIR}/.env"             .
cp -r "${SCRIPT_DIR}/app"           .
cp -r "${SCRIPT_DIR}/datasets"      .

# ── 5. Commit and push ────────────────────────────────────────────────────────
echo "[5/6] Committing and pushing to Hugging Face..."
git add -A
git commit -m "QUANT-X Engine v1.0 — initial deployment" || echo "Nothing to commit."
git push origin main

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "[6/6] Deployment complete!"
echo ""
echo "============================================================"
echo "  Live URL (available in ~2-3 min after build):"
echo "  https://${HF_USERNAME}-${SPACE_NAME}.hf.space"
echo ""
echo "  API Docs:"
echo "  https://${HF_USERNAME}-${SPACE_NAME}.hf.space/docs"
echo ""
echo "  Health Check:"
echo "  https://${HF_USERNAME}-${SPACE_NAME}.hf.space/health"
echo ""
echo "  NEXT STEP — Add UptimeRobot monitor:"
echo "  https://uptimerobot.com (free)"
echo "  URL: https://${HF_USERNAME}-${SPACE_NAME}.hf.space/health"
echo "  Interval: every 10 minutes"
echo "============================================================"

