#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Main / Command line tool """
import logging
logger = logging.getLogger()

import json
import sys
import argparse
import os
from datetime import datetime
import pid


try:
    from .configcontext import ConfigurationContext
except Exception: #ImportError
    from configcontext import ConfigurationContext

try:
    from .eventpipeline import *
except Exception: #ImportError
    from eventpipeline import *

try:
    from .solrinput import SolrStatisticsInput
except Exception: #ImportError
    from solrinput import SolrStatisticsInput

try:
    from .dspacefilter import DSpaceDBFilter
except Exception: #ImportError
    from dspacefilter import DSpaceDBFilter

try:
    from .sessionfilter import SimpleHashSessionFilter
except Exception: #ImportError
    from sessionfilter import SimpleHashSessionFilter

try:
    from .matomooutput import MatomoFilter, MatomoOutput, MatomoOfflineException
except Exception: #ImportError
   from matomooutput import MatomoFilter, MatomoOutput, MatomoBulkOutput

try:
    from .counterfilter import COUNTERRobotsFilter
except Exception: #ImportError
   from counterfilter import COUNTERRobotsFilter


DESCRIPTION = """
Collects Usage stats from DSpace repositories.
"""
class EventPipelineBuilder:

    def build(self, configContext):
        return EventPipeline(
            SolrStatisticsInput(configContext),
            [
                COUNTERRobotsFilter(configContext),
                DSpaceDBFilter(configContext),
                SimpleHashSessionFilter(configContext),
                MatomoFilter(configContext)
            ],
            MatomoOutput(configContext)) 


def main():
    
    try:
        # run with pid locking mecanism
        with pid.PidFile(pidname='/tmp/dspace_collector.pid') as p:
            run()
    
    # PidFileError captures locking problems or already running instances
    except pid.PidFileError as e:
        logger.error("Dspace Stats Collector is already running. Error was: %s" % e)


def run():

    args = parse_args()

    if not os.path.exists(args.config_dir) :
        os.mkdir(args.config_dir)

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    if args.debug:
        loglevel = logging.DEBUG
    
    logDirName = os.path.expanduser('~') + "/dspace-stats-collector/var/logs"
    if not os.path.exists(logDirName):
        os.makedirs(logDirName)

    if args.date_from:
        logFileName = "dspace-stats-collector."+args.date_from.strftime("%Y-%m-%d")+".log"
    else:
        logFileName = "dspace-stats-collector.log"
    
    logging_handlers = [ logging.FileHandler("{}/{}".format(logDirName, logFileName), 'w+') ]

    # if we are in verbose mode, also log to console
    if args.verbose:
        logging_handlers.append(logging.StreamHandler())


    logging.basicConfig(level=loglevel,
                        format="%(asctime)s %(levelname)s: %(message)s",
                        handlers=logging_handlers)

    logger.debug("Verbose: %s" % args.verbose)
    logger.debug("Repository: %s" % args.repository)
    logger.debug("Configuration Directory: %s" % args.config_dir)
    logger.debug("Archived core year selected: %s" % args.archived_core)
    
    if args.date_from:
        logger.debug("Date from: %s" % args.date_from.strftime("%Y-%m-%d"))

    if args.date_until:
        logger.debug("Date until: %s" % args.date_until.strftime("%Y-%m-%d"))

    #for repoName in args.repositories:
    repoName=args.repository

    try:
        configContext = ConfigurationContext(repoName, args)    
    except Exception as e:
        logger.error("Error while loading configuration: %s" % e)
        sys.exit(1)

    if args.date_from:
        logger.debug("Start processing: %s on: %s from date: %s" % (repoName, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), args.date_from.strftime("%Y-%m-%d")))
    else:
        logger.debug("Start processing: %s on: %s from date: %s" % (repoName, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), configContext.history.get_last_tracked_timestamp()))
        
    eventPipeline = EventPipelineBuilder().build(configContext)

    try:    
        eventPipeline.run()

    except MatomoOfflineException as e:
        logger.error("Matomo is offline. Events will be processed in the next run. Error was: %s" % e)
    
    except Exception as e:
        logger.error("Unknown exception. Events will be processed in the next run. Error was: %s" % e)
    
    # close all open resources in configContext (ie: dbconnection)
    configContext.close()


    logger.debug("Repo succesfully processed: %s on: %s " % (repoName, datetime.now().strftime("%Y-%m-%d %H:%M:%S")) )

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
    parser.add_argument("-r", "--repository",
                        metavar="REPOSITORYNAME",
                        default=ConfigurationContext.defaultRepository,
                        help="name of repository to collect usage stats from. Should match the name of the corresponding .properties files in config dir")
    parser.add_argument("-f", "--date_from",
                        type=valid_date_type,
                        metavar="YYYY-MM-DD",
                        default=None,
                        #default=datetime.today(),
                        help="collect events only from this date")
    parser.add_argument("-c",
                        "--config_dir",
                        metavar="DIR",
                        default=ConfigurationContext.defaultConfigPath,
                        help="path to configuration directory")
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        default=False,
                        action="store_true")
    parser.add_argument("--debug",
                        help="debug mode",
                        default=False,
                        action="store_true")
    
    parser.add_argument("-a",
                        "--archived_core",
                        metavar="YYYY",
                        help="previous year corresponding to a sharded statistics corer",
                        default=None)
    parser.add_argument("-u",
                        "--date_until",
                        type=valid_date_type,
                        metavar="YYYY-MM-DD",
                        default=None,
                        help="collect events until this date")
    return parser.parse_args()


if __name__ == "__main__":
    main()
