# This directory is the source of truth for DNS

`kiwihacks.org.yaml` and `kiwihacks.com.yaml` were imported from Cloudflare on
2026-11-08 by `./scripts/bootstrap.sh` and verified with `make plan`, which
reported no changes. They are an exact mirror of the live zones.

Do not hand write these files from scratch. octoDNS treats whatever is here as
the complete desired state of the zone, so a record that is missing from these
files is a record octoDNS will delete from Cloudflare.

To change DNS: edit the file, `make plan` to see the diff, then open a pull
request. The plan workflow comments the exact record diff for a reviewer, and
merging to main applies it.

Trailing dots matter on CNAME, MX, NS and PTR values. An `octodns: cloudflare:
proxied: true` block is the orange cloud: remove it and the origin IP becomes
public.
