# DSpace Stats Collector

[![PyPI version](https://img.shields.io/pypi/v/dspace-stats-collector.svg)](https://pypi.python.org/pypi/dspace-stats-collector)
[![License](https://img.shields.io/pypi/l/dspace-stats-collector.svg)](https://pypi.python.org/pypi/dspace-stats-collector)

## Overview

DSpace Stats Collector is a Python agent that reads usage events from a DSpace repository, enriches them with repository metadata, filters robot traffic, and sends the resulting events to a Matomo tracker.

It is designed as a lightweight, read-only collector for repository operators who need to share DSpace usage statistics with an external usage statistics service or regional aggregator.

## How It Works

The collector follows a pipe-and-filter workflow:

1. Read item views and bitstream downloads from the DSpace Solr statistics core.
2. Filter robot traffic using the COUNTER robots list.
3. Enrich events with item and bitstream metadata from the DSpace database.
4. Build session and IP handling fields.
5. Send events to Matomo through the bulk tracking API.

## Requirements

- Linux-based operating system.
- A non-root operating user for installation and execution.
- `curl`, `git`, and `cron` available on the system.
- DSpace 4 or newer, including supported DSpace CRIS deployments.
- PostgreSQL for the current stable installer profile. Oracle remains a legacy profile and is not included in the stable runtime profile.
- Python 3.10 or newer, or the installer-managed Miniconda fallback.

## Quick Install

Run the installer as the final operating user, not as `root`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)
```

The installer creates a self-contained installation under:

- `~/dspace-stats-collector/bin`
- `~/dspace-stats-collector/config`

It selects the highest versioned release reference by default, uses a local virtual environment when possible, and falls back to a local Miniconda runtime when needed.

Advanced installer options are documented in [installer/README.md](installer/README.md).

## Configuration

The collector reads repository settings from:

```text
~/dspace-stats-collector/config/default.properties
```

At minimum, configure:

- Matomo tracker URL, site ID, and token.
- Repository identifier and country.
- DSpace installation directory.
- DSpace major version.
- Solr server URL, when it cannot be detected from the DSpace configuration.

You can generate a default template with:

```bash
~/dspace-stats-collector/bin/dspace-stats-configure -c ~/dspace-stats-collector/config -r default
```

## First Run

Before enabling scheduled execution, run the collector manually for a known start date:

```bash
~/dspace-stats-collector/bin/dspace-stats-collector -f YYYY-MM-DD --verbose -c ~/dspace-stats-collector/config
```

Review the log file created under:

```text
~/dspace-stats-collector/var/logs/
```

## Cron Setup

After a successful manual run, install the scheduled job:

```bash
~/dspace-stats-collector/bin/dspace-stats-cronify
```

## Historical Export

For coordinated backfill, historical review, or recovery workflows, the collector includes `dspace-stats-export`. It runs the same input and filtering pipeline as the regular collector, but writes the resulting Matomo tracking requests to a local compressed file instead of sending them directly to Matomo.

Export a complete month:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y YYYY -m M
```

Export a date range of up to 31 days:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -f YYYY-MM-DD -u YYYY-MM-DD
```

The command writes the output in the current working directory using this filename pattern:

```text
dspace_stats_export_<idSite>_<YYYY>_<MM>.txt.gz
```

Historical exports can be resource-intensive because they read from Solr and enrich events through the DSpace database. Run them during low-traffic windows, export one month at a time for long periods, and coordinate file delivery with the receiving aggregator. LA Referencia deployments should follow the Spanish [historical export guide](EXPORT.md) before using this workflow in production.

## Available Commands

- `dspace-stats-collector`: collect and send usage events to Matomo.
- `dspace-stats-configure`: create default configuration files.
- `dspace-stats-cronify`: install the collector in the current user's crontab.
- `dspace-stats-export`: export historical events for coordinated backfill workflows.

## LA Referencia Deployments

Repositories that report usage statistics through the LA Referencia ecosystem should follow the Spanish operational guide: [README-LAREFERENCIA.md](README-LAREFERENCIA.md).

That guide includes the LA Referencia configuration generator workflow, national node coordination, Matomo validation steps, and production cron activation sequence.

## More Documentation

- [Installer reference](installer/README.md)
- [Uninstall guide](UNINSTALL.md)
- [Historical export guide](EXPORT.md)

## Background and Credits

This project was developed as part of LA Referencia and OpenAIRE usage statistics work. Historical background and credits are available in [HISTORY.rst](HISTORY.rst).
