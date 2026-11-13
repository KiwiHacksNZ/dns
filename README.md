# KiwiHacks DNS

DNS for `kiwihacks.org` and `kiwihacks.com` as code, managed with
[octoDNS](https://github.com/octodns/octodns). Both zones live on Cloudflare
(nameservers `jerry.ns.cloudflare.com` and `delilah.ns.cloudflare.com`).

The point: every DNS change goes through a pull request, the diff is visible
before it lands, and the history of who changed what is in git rather than in
one person's Cloudflare dashboard.

## Reference

- octoDNS docs: https://github.com/octodns/octodns
- Cloudflare provider: https://github.com/octodns/octodns-cloudflare
- A snapshot of the records observed before the import:
  `reference/observed-2026-11-08.md`
