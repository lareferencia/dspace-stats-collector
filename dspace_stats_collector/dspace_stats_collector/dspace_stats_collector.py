#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Main / Command line tool """

import logging
logger = logging.getLogger()

import json
import sys
import argparse
import os
import datetime

from configcontext import ConfigurationContext
from eventpipeline import *

from solrinput import SolrStatisticsInput
from dspacefilter import DSpaceDBFilter
from sessionfilter import SimpleHashSessionFilter
from matomooutput import MatomoFilter, MatomoOutput
from elasticoutput import ElasticsearchOutput

DESCRIPTION = """
Collects Usage stats from DSpace repositories.
"""
class EventPipelineBuilder:

    def build(self, configContext):
        return EventPipeline(
            SolrStatisticsInput(configContext),
            [
                DSpaceDBFilter(configContext),
                SimpleHashSessionFilter(configContext),
                MatomoFilter(configContext)
            ],
            [MatomoOutput(configContext), ElasticsearchOutput(configContext)])


def main(args, loglevel):

    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)
    logger.debug("Verbose: %s" % args.verbose)
    logger.debug("Repositories: %s" % args.repositories)
    logger.debug("Configuration Directory: %s" % args.config_dir)
    logger.debug("Limit: %s" % args.limit)
    if args.date_from:
        logger.debug("Date from: %s" % args.date_from.strftime("%Y-%m-%d"))

    for repoName in args.repositories:
        logger.debug("START: %s" % repoName)
        
        configContext = ConfigurationContext(repoName, args)

        eventPipeline = EventPipelineBuilder().build(configContext)
        eventPipeline.run()
        logger.debug("END: %s" % repoName)

def parse_args():

    def valid_date_type(arg_date_str):
        """custom argparse *date* type for user dates values given from the command line"""
        # https://gist.github.com/monkut/e60eea811ef085a6540f
        try:
            return datetime.strptime(arg_date_str, "%Y-%m-%d")
        except ValueError:
            msg = "Given Date ({0}) not valid! Expected format, YYYY-MM-DD!".format(arg_date_str)
            raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("repositories",
                        metavar="REPOSITORYNAME",
                        nargs="+",
                        help="name of repositories to collect usage stats from. Should match the name of the corresponding .properties files in config dir")
    parser.add_argument("-f", "--date_from",
                        type=valid_date_type,
                        metavar="YYYY-MM-DD",
                        default=None,
                        help="collect events only from this date")
    parser.add_argument("-l",
                        "--limit",
                        metavar="LIMIT",
                        type=int,
                        help="max number of events to output")
    parser.add_argument("-c",
                        "--config_dir",
                        metavar="DIR",
                        default="{}/config".format(os.path.dirname(os.path.realpath(__file__))),
                        help="path to configuration directory")
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        default=False,
                        action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    main(args, loglevel)

