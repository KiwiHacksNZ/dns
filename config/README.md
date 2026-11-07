# This directory is the source of truth for DNS

It is EMPTY until someone runs `./scripts/bootstrap.sh`, which pulls the live
Cloudflare records down into `kiwihacks.org.yaml` and `kiwihacks.com.yaml`.

Do not hand write these files from scratch. octoDNS treats whatever is here as
the complete desired state of the zone, so a record that is missing from these
files is a record octoDNS will delete from Cloudflare. The first version of
these files has to come from `octodns-dump` so it is an exact mirror.

Once the dump is in, edit these files normally and open a pull request.
