#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Cron Installer / Command line tool """
import logging
logger = logging.getLogger()

import os
import argparse

try:
    from .configcontext import ConfigurationContext
except Exception: #ImportError
    from configcontext import ConfigurationContext

from crontab import CronTab

DESCRIPTION = """
Installs collector command in the current user crontab.
"""

def main():

    args = parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)
    logger.debug("Verbose: %s" % args.verbose)

    # use user crontab
    cron = CronTab(user=args.user_cron)

    if args.delete_old_entries:
        for item in cron.find_command(args.command_path):
            cron.remove(item)

    job = cron.new(command=args.command_path)
    job.every(args.run_every_m_minutes).minutes()

    cron.write()

    print("Current tasks in cron: ")
    for item in cron:
        print(item)

def parse_args():

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        default=False,
                        action="store_true")

    parser.add_argument("-u",
                        "--user_cron",
                        help="Current user cron (True) / System cron (False)",
                        default=True)

    parser.add_argument("-d",
                        "--delete_old_entries",
                        help="Delete old entries of the same command",
                        default=True)
    
    parser.add_argument("-m",
                        "--run_every_m_minutes",
                        help="run job every m minutes",
                        type=int,
                        default=59)

    parser.add_argument("-c",
                        "--command_path",
                        metavar="DIR",
                        default="{}/bin/{}".format(ConfigurationContext.defaultInstallPath,ConfigurationContext.defaultCollectorCommand),
                        help="full path to command")

    return parser.parse_args()


if __name__ == "__main__":
    main()

