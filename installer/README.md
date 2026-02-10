# DSpace Stats Collector Installer

This directory contains a self-contained installer flow.

## One-line install (Linux)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)
```

By default, stable mode proposes the highest versioned release reference found in remote tags and branches (`vX.Y` or `vX.Y.Z`).
Stable mode uses system Python with `venv` when Python `3.10+` is available.
For compatibility with previous deployments, binaries and configuration are always placed under:

- `~/dspace-stats-collector/bin`
- `~/dspace-stats-collector/config`

On reinstall/update, the installer automatically preserves previous `config` and `var/state`.
Stable profile is PostgreSQL-only (Oracle is not included).

## Non-interactive examples

Stable tag install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --tag v1.0
```

Stable branch install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --ref branch:v1.0
```

Development editable install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --dev --branch develop
```

## Included runtime profiles

- `requirements/legacy-py38.txt`
- `requirements/stable-py310.txt`
