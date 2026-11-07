#!/usr/bin/env bash
# One time bootstrap: pull the live Cloudflare records down into config/ so the
# repo becomes an exact mirror of what is already serving. Run this ONCE, on a
# clean checkout, before you change anything.
#
#   1. Create a Cloudflare API token (Zone:Read + DNS:Edit on both zones)
#   2. cp .env.example .env  and paste the token in
#   3. ./scripts/bootstrap.sh
#   4. Read the generated config/*.yaml and sanity check them
#   5. make plan   <- MUST say "No changes were planned" before you trust it
#
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found. Copy .env.example to .env and add your Cloudflare token."
  exit 1
fi
set -a; . ./.env; set +a

if [ -z "${CLOUDFLARE_TOKEN:-}" ]; then
  echo "CLOUDFLARE_TOKEN is empty in .env"
  exit 1
fi

make venv

for zone in kiwihacks.org. kiwihacks.com.; do
  echo "Dumping $zone from Cloudflare..."
  .venv/bin/octodns-dump --config-file ./config.yaml --output-dir ./config "$zone" cloudflare
done

echo
echo "Dump complete. Files written:"
ls -la config/

echo
echo "Now run 'make plan'. It must report no changes. If it wants to change or"
echo "delete anything, the dump did not round trip cleanly: stop and work out why"
echo "before you run 'make apply'."
