# DSpace Usage Stats Collector Uninstall Guide

If you need to fully remove DSpace Usage Stats Collector, follow these steps.

## 1. Remove installation directory

Delete the installation folder from the home directory of the user that installed the collector:

```bash
rm -rf ~/dspace-stats-collector
```

## 2. Remove scheduled execution from cron

Edit the same user's crontab:

```bash
crontab -e
```

Find and remove the collector entry (example):

```bash
*/59 * * * * /home/username/dspace-stats-collector/bin/dspace-stats-collector
```

Save and close the file.

## 3. Optional cleanup

If you downloaded installer scripts manually to temporary folders, remove those files as needed.
