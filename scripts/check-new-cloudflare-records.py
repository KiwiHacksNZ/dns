#!/usr/bin/env python3
"""Find Cloudflare records that exist live but are missing from this repo.

Used by .github/workflows/check-cloudflare-drift.yml. It takes two octoDNS
markdown plans, both made against the live Cloudflare zones:

  --base   plan made with the BASE branch's config (what main says today)
  --head   plan made with the PR branch's config (what merging would apply)

octoDNS plans a "Delete" for a record that is live but not in the YAML, and an
"Update" for a record whose live value differs from the YAML. In the base plan
those are exactly the changes someone made in Cloudflare without a PR.

A record is reported only if it shows up in BOTH plans. If the PR already adds
it (or corrects it), the head plan no longer touches it and it is not reported.
If the PR deliberately deletes a record, the base plan has no Delete for it
(live and main agree), so that is not reported either.

Exit status is always 0. The answer is written to --out as a PR comment body,
and to $GITHUB_OUTPUT as found=true or found=false, so the workflow decides
what to do with it.
"""
import argparse
import os
import sys

MARKER = "<!-- cloudflare-drift -->"


def parse(path):
    """Return {(zone, name, type): operation} for the Delete and Update rows."""
    zone = None
    last = None
    found = {}
    with open(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("## "):
                zone = line[3:].strip()
                last = None
                continue
            if not line.startswith("|") or line.startswith("|--") or line.startswith("| Operation"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            if len(cells) < 3 or zone is None:
                continue
            op, name, rtype = cells[0], cells[1], cells[2]
            if not op and last:
                # Continuation row of an Update (the new value): same record.
                continue
            last = (op, name, rtype)
            if op in ("Delete", "Update"):
                found[(zone, name, rtype)] = op
    return found


def fqdn(zone, name):
    zone = zone.rstrip(".")
    return zone if not name else f"{name}.{zone}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = parse(args.base)
    head = parse(args.head)
    unsynced = sorted(k for k in base if k in head)

    if unsynced:
        lines = [
            MARKER,
            "### Cloudflare has records this branch does not know about",
            "",
            "These changed in Cloudflare outside the repo and are not in the "
            "config on the base branch or in this PR. **Merging will delete or "
            "overwrite them.**",
            "",
            "| Record | Type | In Cloudflare |",
            "|--|--|--|",
        ]
        for zone, name, rtype in unsynced:
            state = "new, not in the repo" if base[(zone, name, rtype)] == "Delete" else "differs from the repo"
            lines.append(f"| `{fqdn(zone, name)}` | {rtype} | {state} |")
        lines += [
            "",
            "To fix it, either:",
            "- merge the automated `Sync Cloudflare records` PR first and update this branch, or",
            "- run `make dump` and copy the new records into this branch's `config/` files.",
            "",
            "If a record really should be removed from Cloudflare, confirm that with "
            "whoever created it before merging.",
        ]
    else:
        lines = [
            MARKER,
            "### Cloudflare drift check",
            "",
            "No records in Cloudflare are missing from this branch.",
        ]

    with open(args.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    for zone, name, rtype in unsynced:
        print(f"unsynced: {fqdn(zone, name)} {rtype} ({base[(zone, name, rtype)]})")
    print(f"{len(unsynced)} unsynced record(s)")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as fh:
            fh.write(f"found={'true' if unsynced else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
