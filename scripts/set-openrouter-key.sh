#!/usr/bin/env bash
# Store an OpenRouter API key in this repo's .env (gitignored, chmod 600) for the Jev vs Kev benchmark.
#
#   ./scripts/set-openrouter-key.sh            # prompts; input is hidden
#   pbpaste | ./scripts/set-openrouter-key.sh  # or pipe it from the clipboard
#
# The key is checked against OpenRouter and its label is shown so you can confirm it is the
# general-purpose key, not the FLS one. The key itself is never printed.
set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"

if [ -t 0 ]; then
  read -r -s -p "OpenRouter API key (general purpose, not FLS): " key
  echo
else
  read -r key || true
fi
key="$(printf '%s' "$key" | tr -d '[:space:]')"

if [[ "$key" != sk-or-* ]]; then
  echo "That doesn't look like an OpenRouter key (expected it to start with sk-or-). Nothing saved." >&2
  exit 1
fi

# Validate and fetch the key's label; the header goes via stdin so the key never appears in `ps`.
info="$(printf 'Authorization: Bearer %s\n' "$key" | curl -sS -H @- https://openrouter.ai/api/v1/key)" || {
  echo "Could not reach OpenRouter to check the key. Nothing saved." >&2
  exit 1
}
label="$(printf '%s' "$info" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["data"].get("label") or "(no label)")' 2>/dev/null)" || {
  echo "OpenRouter rejected the key: $info" >&2
  exit 1
}
usage="$(printf '%s' "$info" | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print("usage $%.2f, limit %s" % (d.get("usage") or 0, d.get("limit") or "none"))')"

echo "Key OK: label \"$label\" ($usage), ending …${key: -4}"
if printf '%s' "$label" | grep -qi 'fls'; then
  if [ -t 0 ]; then
    read -r -p "That label mentions FLS. Save it anyway? [y/N] " yn
  else
    yn=n
  fi
  [[ "$yn" =~ ^[Yy]$ ]] || { echo "Not saved." >&2; exit 1; }
fi

touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
tmp="$(mktemp)"
grep -v '^OPENROUTER_API_KEY=' "$ENV_FILE" > "$tmp" || true
printf 'OPENROUTER_API_KEY=%s\n' "$key" >> "$tmp"
cat "$tmp" > "$ENV_FILE"
rm -f "$tmp"
echo "Saved to $ENV_FILE"
