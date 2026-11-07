# KiwiHacks DNS. Run `make help` for the short version.
SHELL := /bin/bash
VENV  := .venv
PY    := $(VENV)/bin/python
OCTO  := $(VENV)/bin

.PHONY: help venv dump validate plan apply clean

help:
	@echo "make venv      install octoDNS into .venv"
	@echo "make dump      pull the live Cloudflare records into config/ (first run only)"
	@echo "make validate  check the YAML parses and the records are well formed"
	@echo "make plan      show what would change in Cloudflare (read only, safe)"
	@echo "make apply     actually push the changes to Cloudflare"

venv: $(VENV)/.installed
$(VENV)/.installed: requirements.txt
	uv venv --python 3.12 $(VENV)
	VIRTUAL_ENV=$(VENV) uv pip install -r requirements.txt
	touch $@

dump: venv
	set -a; [ -f .env ] && . ./.env; set +a; \
	$(OCTO)/octodns-dump --config-file ./config.yaml --output-dir ./config kiwihacks.org. cloudflare && \
	$(OCTO)/octodns-dump --config-file ./config.yaml --output-dir ./config kiwihacks.com. cloudflare

validate: venv
	set -a; [ -f .env ] && . ./.env; set +a; \
	$(OCTO)/octodns-validate --config-file ./config.yaml

plan: venv
	set -a; [ -f .env ] && . ./.env; set +a; \
	$(OCTO)/octodns-sync --config-file ./config.yaml

apply: venv
	@echo "This writes to live DNS for kiwihacks.org and kiwihacks.com."
	@read -p "Type yes to continue: " ok; [ "$$ok" = "yes" ]
	set -a; [ -f .env ] && . ./.env; set +a; \
	$(OCTO)/octodns-sync --config-file ./config.yaml --doit

clean:
	rm -rf $(VENV)
