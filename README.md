# KiwiHacks DNS

DNS for `kiwihacks.org` and `kiwihacks.com` as code, managed with
[octoDNS](https://github.com/octodns/octodns). Both zones live on Cloudflare
(nameservers `jerry.ns.cloudflare.com` and `delilah.ns.cloudflare.com`).

The point: every DNS change goes through a pull request, the diff is visible
before it lands, and the history of who changed what is in git rather than in
one person's Cloudflare dashboard. When KiwiHacks gets handed to the next
generation, the zones come with it.

## How it fits together

```
config/kiwihacks.org.yaml   what the zone SHOULD look like  (source of truth)
config/kiwihacks.com.yaml
config.yaml                 wiring: read from config/, write to Cloudflare
.github/workflows/plan.yml  on every PR, show the record diff as a comment
.github/workflows/apply.yml on merge to main, push the change to Cloudflare
```

The files in `config/` are the complete desired state of each zone. Anything
not in them gets deleted from Cloudflare on the next apply. That is the whole
idea, and it is also the sharp edge, so read the bootstrap section before you
touch anything.

---

## First time setup

Already done on 2026-11-08: both zones are imported and `make plan` reports no
changes. This section is kept as the record of how it was set up, and for
anyone rebuilding it from scratch or adding another zone.

Do these in order. Steps 1 and 2 are the only ones that need a human with
Cloudflare admin access.

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

## Reference

- octoDNS docs: https://github.com/octodns/octodns
- Cloudflare provider: https://github.com/octodns/octodns-cloudflare
- A snapshot of the records observed before the import:
  `reference/observed-2026-11-08.md`
