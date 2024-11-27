#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Main / Command line tool """
import logging
logger = logging.getLogger()

import json
import sys
import argparse
import os
from datetime import datetime, timedelta


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
    from .matomooutput import MatomoFilter
except Exception: #ImportError
   from matomooutput import MatomoFilter

try:
    from .fileoutput import FileOutput
except Exception: #ImportError
   from fileoutput import FileOutput


try:
    from .counterfilter import COUNTERRobotsFilter
except Exception: #ImportError
   from counterfilter import COUNTERRobotsFilter


DESCRIPTION = """
Export Usage stats from DSpace repositories.
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
            FileOutput(configContext)) 


def main():
    
    try:
        run()
    except Exception as e:
        logger.error("An error occurred: %s" % e)
        sys.exit(1)

def run():

    args = parse_args()

    if not os.path.exists(args.config_dir) :
        os.mkdir(args.config_dir)

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
   
    logger.debug("Verbose: %s" % args.verbose)
    logger.debug("Configuration Directory: %s" % args.config_dir)
    logger.debug("Archived core year selected: %s" % args.archived_core)

    # setup logging
    logging.basicConfig(level=loglevel, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Verificar si date_from y date_until están presentes
    if args.date_from and args.date_until:
        # Ajustar date_from al inicio del día
        args.date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        args.date_from = args.date_from.replace(hour=0, minute=0, second=0)

        # Ajustar date_until al inicio del día siguiente adicionando un día a la fecha
        args.date_until = datetime.strptime(args.date_until, "%Y-%m-%d")
        args.date_until = args.date_until + timedelta(days=1)
        args.date_until = args.date_until.replace(hour=0, minute=0, second=0)
        
    else:
        # Calcular date_from y date_until basado en year y month
        if args.year and args.month:
            args.date_from = datetime(args.year, args.month, 1, 0, 0, 0)

            if args.month == 12:
                args.date_until = datetime(args.year + 1, 1, 1, 0, 0, 0)
            else:
                args.date_until = datetime(args.year, args.month + 1, 1, 0, 0, 0)
        else:
            logger.error("Debe especificar year y month o date_from y date_until.")
            return

    # Verificar si la diferencia entre date_from y date_until es mayor a un mes
    if args.date_from and args.date_until:
        if (args.date_until - args.date_from).days > 31:
            logger.error("El periodo entre date_from y date_until debe ser igual o menor a un mes.")
            return

    if args.date_from:
        logger.info("Date from: %s" % args.date_from.strftime("%Y-%m-%d %H:%M:%S"))

    if args.date_until:
        logger.info("Date until: %s" % args.date_until.strftime("%Y-%m-%d %H:%M:%S"))

    ## add no_limit flag to args
    args.no_limit = True

    repoName='default'

    try:
        configContext = ConfigurationContext(repoName, args)    
    except Exception as e:
        logger.error("Error while loading configuration: %s" % e)
        sys.exit(1)
      

    try:    
        eventPipeline = EventPipelineBuilder().build(configContext)
        eventPipeline.run()
  
    except Exception as e:
        logger.error("Unknown exception. Error was: %s" % e)
        traceback.print_exc()
    
    # close all open resources in configContext (ie: dbconnection)
    configContext.close()

    logger.info("DSpace Stats Collector finished export from %s to %s" % (configContext.solrQueryInitialTimestamp, configContext.history.get_last_tracked_timestamp()))


def parse_args():

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    
    # year to be processed is mandatory
    parser.add_argument("-y", "--year", type=int, help="year to be processed")

    # month to be processed is mandatory
    parser.add_argument("-m", "--month", type=int, help="month to be processed")

    # date from
    parser.add_argument("-f", "--date_from", help="date from")

    # date until
    parser.add_argument("-u", "--date_until", help="date until")
    
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
    
    parser.add_argument("-a",
                        "--archived_core",
                        metavar="YYYY",
                        help="previous year corresponding to a sharded statistics corer",
                        default=None)
    
    return parser.parse_args()


if __name__ == "__main__":
    main()
