#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Cron Installer / Command line tool """
import logging
logger = logging.getLogger()

import os
import argparse
import time
import pkg_resources
import shutil
import urllib.request

from string import Template

try:
    from .configcontext import ConfigurationContext
except Exception: #ImportError
    from configcontext import ConfigurationContext


DESCRIPTION = """
Configuration tool.
"""

CONFIG_TEMPLATE = Template("""

# ask your node admin for this information
matomo.idSite = $site_id
matomo.token_auth = $matomo_token_auth

# repository id (ie: OpenDOAR ID)
matomo.repositoryId = $repository_id

# country iso 2 chars (Example: CL)
matomo.countryISO = XX 

# dspace instalation dir
dspace.dir = $dspace_dir

# dspace version 1 char only (4,5,6)
dspace.majorVersion = $dspace_major_version

# default solr server url 
solr.server = http://localhost:8080/solr

# default max number of events to send
max.eventsToSend = $max_events

# please do not modify this values
matomo.rec = 1
matomo.batchSize = 50
matomo.trackerUrl = http://matomo.lareferencia.info/matomo.php

# anonymize ip
# 255.255.255.255 -> original ip (default)
# 255.255.255.0   -> 1 byte anonymize Ex. 192.168.100.12 --> 192.168.100.0 
# 255.255.0.0     -> 2 byte anonimize Ex. 192.168.100.12 --> 192.168.0.0
anonymize.ip_mask = 255.255.255.255
""")

def main():

    args = parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)
    logger.debug("Verbose: %s" % args.verbose)

    # default values
    site_id = "MATOMO SITE ID"
    repository_id = "UNIQUE REPOSITORY ID (OpenDOAR)"
    matomo_token_auth = "MATOMO TOKEN AUTH"

    dspace_dir = "/dspace"
    dspace_major_version = 6
    max_events = 100

    # instantiate config template with default values
    config_str = CONFIG_TEMPLATE.substitute(site_id=site_id, repository_id = repository_id, matomo_token_auth=matomo_token_auth, dspace_dir=dspace_dir, dspace_major_version=dspace_major_version, max_events=max_events)

    # create config dir if not exists
    if not os.path.exists(args.config_dir) :
        print("Creating config dir %s" % (args.config_dir)) 
        os.mkdir(args.config_dir)
    else:
        print("Config dir %s found!" % (args.config_dir)) 

    # obtaing config_file path
    config_file_path = ConfigurationContext.getPropertiesFieldPath(args.config_dir, args.repository)
    
    # if config file exists rename it using current timestamp
    if os.path.exists(config_file_path) :
        new_filename = config_file_path + time.strftime(".%Y%m%d%H%M%S")
        os.rename(config_file_path, new_filename)
        print("Config file %s already exists! renaming existings file to %s" % (config_file_path, new_filename)) 
 
    # write contents in config file
    print("Saving config settings in %s" % (config_file_path)) 
    config_file = open(config_file_path,"w+")
    config_file.write(config_str)
    config_file.close()

    print("Installing counter robots file in %s " % (args.config_dir)) 

    try:
        with urllib.request.urlopen('https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/config/COUNTER_Robots_list.json') as response:
            filedata = response.read()
            with open(args.config_dir + '/' + ConfigurationContext.counterRobotsFileName, 'wb') as f:
                f.write(filedata)
    except Exception as e:
        print("Error loading and installing counter robots json file. {}".format(e))   
    


def parse_args():

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("-r", "--repository",
                        metavar="REPOSITORYNAME",
                        default=ConfigurationContext.defaultRepository,
                        help="Name of repository to collect usage stats from. This command will generate the corresponding .properties files in config dir")

    parser.add_argument("-c",
                        "--config_dir",
                        metavar="DIR",
                        default=ConfigurationContext.defaultConfigPath,
                        help="Path to configuration directory")

    parser.add_argument("-v",
                        "--verbose",
                        help="Increase output verbosity",
                        default=False,
                        action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()

