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
matomo.trackerUrl = http://matomo.lareferencia.info/matomo.php
matomo.idSite = $site_id
matomo.repositoryId = $repository_id 
matomo.token_auth = $matomo_token_auth
matomo.rec = 1
matomo.batchSize = 50

dspace.dir = $dspace_dir
dspace.majorVersion = $dspace_major_version
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

    dspace_dir = "/home/dspace"
    dspace_major_version = 6

    # instantiate config template with default values
    config_str = CONFIG_TEMPLATE.substitute(site_id=site_id, repository_id = repository_id, matomo_token_auth=matomo_token_auth, dspace_dir=dspace_dir, dspace_major_version=dspace_major_version)

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

