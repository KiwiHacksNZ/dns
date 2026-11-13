## How it fits together

```
config/kiwihacks.org.yaml   what the zone SHOULD look like  (source of truth)
config/kiwihacks.com.yaml
config.yaml                 wiring: read from config/, write to Cloudflare
.github/workflows/plan.yml  on every PR, show the record diff as a comment
.github/workflows/apply.yml on merge to main, push the change to Cloudflare
.github/workflows/sync-cloudflare.yml        daily, open a PR with any records added in Cloudflare by hand
.github/workflows/check-cloudflare-drift.yml on every PR, fail if Cloudflare has records the PR would delete
scripts/check-new-cloudflare-records.py      the logic behind that last check
```

The files in `config/` are the complete desired state of each zone. Anything
not in them gets deleted from Cloudflare on the next apply. That is the whole
idea, and it is also the sharp edge, so read the bootstrap section before you
touch anything.

---

## First time setup

### 1. Create a Cloudflare API token

At https://dash.cloudflare.com/profile/api-tokens, "Create Token", "Create
Custom Token":

| Setting | Value |
|---|---|
| Permissions | `Zone` / `Zone` / `Read` |
| Permissions | `Zone` / `DNS` / `Edit` |
| Zone Resources | Include / Specific zone / `kiwihacks.org` |
| Zone Resources | Include / Specific zone / `kiwihacks.com` |
| TTL | leave open, or set a review date |

Do not use the Global API Key. It can do everything on the account including
billing, and it cannot be scoped. The token above can only read and write DNS
records on those two zones, which is exactly what octoDNS needs.

### 2. Put the token in two places

Locally, for running plans on your laptop:

```bash
cp .env.example .env
# paste the token into .env
```

And as a GitHub Actions secret, so CI can do the applies:

```bash
gh secret set CLOUDFLARE_TOKEN --repo KiwiHacksNZ/dns
```

`.env` is gitignored. Never commit the token.

### 3. Pull the live records down

This is the step that makes the repo an honest mirror of reality. It reads
Cloudflare and writes `config/kiwihacks.org.yaml` and
`config/kiwihacks.com.yaml`.

```bash
./scripts/bootstrap.sh
```

### 4. Prove the round trip is clean

```bash
make plan
```

This MUST report no changes for both zones. If octoDNS wants to add, change or
delete anything at this point, the dump did not round trip cleanly. Stop.
Work out why, fix the YAML by hand to match reality, and run `make plan` again.
Do not run an apply until the plan is empty.

### 5. Commit and open the first PR

```bash
git add -A
git commit -m "Import live kiwihacks.org and kiwihacks.com zones from Cloudflare"
```

The plan workflow will run on the PR and should also show no changes. That is
your proof that CI has working credentials and agrees with your laptop.

---

## Day to day: changing a record

1. Branch, edit the relevant file in `config/`
2. `make plan` to see the diff locally
3. Push, open a PR. The bot comments the exact record diff
4. Someone reads the diff and approves
5. Merge. The apply workflow pushes it to Cloudflare

Example, adding a subdomain pointing at Vercel:

```yaml
# in config/kiwihacks.org.yaml
podium:
  type: CNAME
  value: cname.vercel-dns.com.
```

Trailing dots matter on CNAME, MX, NS and PTR values. octoDNS will tell you if
you forget one.

**Keep the names in alphabetical order.** The config sets `enforce_order: true`,
so octoDNS refuses to load a zone file whose keys are out of order, with a
`keys out of order: expected X got Y` error. Do not append a new record to the
bottom of the file: insert it where it sorts. This is deliberate, it keeps the
diffs on a 30 record file readable instead of scattering related changes.

### Cloudflare proxying (the orange cloud)

A proxied record carries this in the YAML:

```yaml
'':
  type: A
  values:
    - 104.21.78.251
    - 172.67.138.229
  octodns:
    cloudflare:
      proxied: true
```

If you drop that `octodns:` block, the next apply turns the orange cloud off
and the origin IP becomes public. The bootstrap dump preserves these, so do not
hand edit them away.

---

## Safety

- **The plan is free and read only.** `make plan` and the PR workflow never
  write. Run them as often as you like.
- **octoDNS refuses large destructive changes by default.** If a plan would
  update or delete more than about a third of a zone it errors out rather than
  doing it. That is a seatbelt, not permission to skip reading the diff.
- **Only CI holds the write path.** The apply workflow is gated on a `dns`
  GitHub environment, so you can require a reviewer in the repo settings.
- **Keep the nameservers out of the config.** Cloudflare manages the apex NS
  records itself and octoDNS does not touch them.

## Records added in the Cloudflare dashboard

`config/` is the complete desired state, so a record someone adds in the
Cloudflare dashboard (including the "public hostname" tab of a Tunnel, which
creates a CNAME) is deleted by the next apply. Two workflows catch this:

- **Sync Cloudflare records** runs daily. If Cloudflare has changed, it dumps the
  live zones into `config/` and opens one PR, `automation/sync-cloudflare`.
  Review it and merge. It checks that the result plans no changes before opening
  the PR, and it never pushes to `main`. You can also run it by hand from the
  Actions tab.
- **Cloudflare drift check** runs on every PR and is meant to be a required
  status check (job name `drift`). It fails if Cloudflare has a record that is
  not in `main` and that the PR does not add, and comments which ones. A record
  the PR removes on purpose is not flagged. To clear it, merge the sync PR and
  update your branch, or run `make dump`. It has no path filter on purpose, a
  required check that is skipped never reports and blocks the PR. A PR that does
  not touch `config/` finishes green in a few seconds without calling Cloudflare.

To require it: repo Settings, Branches (or Rules), the rule for `main`, "Require
status checks to pass", add `drift`.

**The daily PR needs a token.** A pull request opened with the default Actions
token does not start other workflows, so it would never get the required drift
check and could not be merged. Create a fine-grained personal access token for
this repo only (Contents and Pull requests, read and write), and save it as the
repo secret `SYNC_PR_TOKEN`. The workflow uses it when present. Without it the
workflow falls back to the default token, which also needs Settings, Actions,
General, "Allow GitHub Actions to create and approve pull requests" (an org
admin may have to enable that at the org level first).

The drift check on a PR is a snapshot, so the apply workflow runs it again right
before it writes to Cloudflare. If a record was added in the dashboard after the
PR passed, the apply stops with the records listed as `unsynced` instead of
deleting them. Merge the sync PR and re-run the apply. For a real emergency, such
as reverting an outage while drift exists, run the apply workflow by hand from the
Actions tab with `skip_drift_check` ticked. Anything unsynced is then deleted, so
follow it up with a sync.

## Breaking glass

If an apply takes the site down, revert the commit and merge the revert. That
re-applies the previous state. Cloudflare changes propagate in seconds at the
TTLs in use here (300s and below). The Cloudflare dashboard still works as a
manual override in a genuine emergency, but anything changed by hand there
gets reverted by the next apply, so follow it up with a matching PR.

## Known drift to look at after the import

These showed up in the live zones and are worth a decision once the import is
in. Do not delete anything until someone confirms, some of them are load
bearing for mail deliverability.

- `kiwihacks.org` still carries a `brevo-code:` TXT record and its DMARC `rua`
  points at `dmarc.brevo.com`. Brevo was removed from the stack in August 2026.
- `kiwihacks.org` SPF includes `_spf.mlsend.com` (MailerLite). Check whether
  that is still sending, now that bulk mail goes through Loops.
- Both zones are at `p=none` DMARC. Moving to `p=quarantine` is a separate
  piece of work, but it is the next thing worth doing for deliverability.
