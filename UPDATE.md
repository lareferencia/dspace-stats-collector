# DSpace Stats Collector Update Guide

Use this process to update an existing installation.
It is not intended for first-time installation.

## Preconditions

- Linux host
- Run as the same user used in the original installation
- `curl` and `git` available in the system

## Recommended update (interactive)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)
```

The installer will:

- Propose the highest versioned release ref found in tags/branches (`vX.Y` or `vX.Y.Z`)
- Keep compatibility paths:
  - `~/dspace-stats-collector/bin`
  - `~/dspace-stats-collector/config`
- Preserve existing `config` and `var/state` during reinstall

## Non-interactive examples

Stable update from tag:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --tag v1.0
```

Stable update from branch:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --ref branch:v1.0
```

Development update (editable):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --dev --branch develop
```
