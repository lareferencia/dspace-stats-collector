#!/usr/bin/env python
#
# -*- coding: utf-8 -*-

"""Main module."""
import json
import sys
import argparse
import logging
import datetime
import json
import hashlib
import requests
import re
import sqlalchemy
from pyjavaprops.javaproperties import JavaProperties
from dateutil import parser as dateutil_parser

logger = logging.getLogger()

DESCRIPTION = """
Collects Usage Stats from DSpace repositories.
Repository names are used to load configuration parameters from <repo_name>.properties file.
"""


class Event:

    _data_dict = {}

    def __init__(self):
        None

    def __getattr__(self, attribute):
        return self._data_dict[attribute]

    def __setattr__(self, name, value):
        self._data_dict[name] = value

    def __str__(self):
        return self._data_dict.__str__()

    def toJSON(self):
        return json.dumps(self._data_dict, indent=4, sort_keys=True)

class EventPipeline:

    _input_stage = None
    _filters_stage = []
    _output_stage = None

    def __init__(self, input, filters, output):
        self._input_stage = input
        self._filters_stage = filters
        self._output_stage = output

    def run(self):
        events = self._input_stage.run()

        for filter in self._filters_stage:
            events = filter.run(events)

        self._output_stage.run(events)


class DummyInput:

    def __init__(self):
        None

    def run(self):
        for x in range(1,5):
            event = Event()
            event.id = "00" + str(x)
            yield event


class FileInput:

    def __init__(self, filename):
        self._filename = filename

    def run(self):
        try:
            with open(self._filename, 'r') as content_file:
                query_result = content_file.read()
            r = json.loads(query_result)
            for doc in r['response']['docs']:
                event = Event()
                event._src = doc
                yield event
        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            logger.exception("Error while trying to read events from {}".format(self._filename))
            raise


class DummyFilter:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            event.url = "http://dummy.org/" + str(event.id)
            yield event


class RepoPropertiesFilter:

    def __init__(self, repoProperties):
        self._repoProperties = repoProperties

    def run(self, events):
        for event in events:
            event._repo = self._repoProperties
            yield event


class SimpleHashSessionFilter:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            srcString = "{:%Y-%m-%d}#{}#{}".format(
                            dateutil_parser.parse(event._src['time']),
                            event._src['ip'],
                            event._src['userAgent']
                        )
            sessDict = {
                        'id': hashlib.md5(srcString.encode()).hexdigest(),
                        'srcString': srcString
                       }
            event._sess = sessDict
            yield event


class MatomoFilter:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            event.cip = event._src['ip']
            event.ua = event._src['userAgent']
            event.timestamp = event._src['time']
            if 'referrer' in event._src.keys():  # Not always available
                event.urlref = event._src['referrer']
            event.rec = event._repo['matomo.rec']
            event.idSite = event._repo['matomo.idSite']
            event.token_auth = event._repo['matomo.token_auth']
            event.idVisit = event._sess['id']
            yield event


class DummyOutput:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            print(event.toJSON())


class EventPipelineBuilder:

    def __init__(self):
        None

    def build(self, repo):
        return EventPipeline(
            FileInput("../tests/sample_input.json"),
            [
                RepoPropertiesFilter(repo.properties),
                SimpleHashSessionFilter(),
                MatomoFilter()
            ],
            DummyOutput())


class Repository:

    def __init__(self, propertiesFilename):
        self.propertiesFilename = propertiesFilename
        self.properties = self._read_properties()
        self.dspaceProperties = self._read_dspace_properties()

        self.solrSession = requests.Session()
        self.solrServer = self._find_solr_server()

        self.db = DSpaceDB(
                        self.dspaceProperties['db.url'],
                        self.dspaceProperties['db.username'],
                        self.dspaceProperties['db.password'],
                        self.dspaceProperties['db.schema']
                    )

    def _read_properties(self):
        javaprops = JavaProperties()

        try:
            javaprops.load(open(self.propertiesFilename))
            property_dict = javaprops.get_property_dict()
        except (FileNotFoundError, UnboundLocalError):
            logger.exception("Error while trying to read properties file %s" % self.propertiesFilename)
            raise

        logger.debug("Read succesfully property file %s" % self.propertiesFilename)
        return property_dict

    def _read_dspace_properties(self):
        javaprops = JavaProperties()

        try:
            propertiesFilename = "%s/config/dspace.cfg" % (self.properties["dspace.dir"])
            javaprops.load(open(propertiesFilename))
            property_dict = javaprops.get_property_dict()
            logger.debug("Read succesfully property file %s" % propertiesFilename)
        except (FileNotFoundError, UnboundLocalError):
            logger.exception("Error while trying to read properties file %s" % propertiesFilename)
            raise

        try:
            propertiesFilename = "%s/config/local.cfg" % (self.properties["dspace.dir"])
            javaprops.load(open(propertiesFilename))
            property_dict = javaprops.get_property_dict()
            logger.debug("Read succesfully property file %s" % propertiesFilename)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not read property file %s" % propertiesFilename)
            pass

        return property_dict

    def _find_solr_server(self):

        # Find server
        solrServer = None
        response = None
        search_path = [
            self.properties['solr.server'] if 'solr.server' in self.properties.keys() else None,
            self.dspaceProperties['solr.server'] if 'solr.server' in self.dspaceProperties.keys() else None
            ]
        for path in search_path:
            if path is None:
                continue
            url = path + "/statistics/admin/ping?wt=json"
            try:
                response = self.solrSession.get(url)
                if response.status_code == 200:
                    solrServer = path
                    break
            except:
                pass

        if solrServer is not None:
            logger.debug("Solr Server found at %s" % solrServer)
        else:
            logger.exception("Solr Server not found in search path: %s" % search_path)
            raise

        # Test Connection
        try:
            status = json.loads(response.text)["status"]
            logger.debug("Solr Statistics Core Status: %s" % status)
        except (KeyError, json.decoder.JSONDecodeError):
            logger.exception("Could not read Solr Statistics Core Status from %s" % solrServer)
            raise

        if status != "OK":
            logger.error("Solr Statistics Core Not Ready")
            raise RuntimeError
        return solrServer


class DSpaceDB:

    def __init__(self, jdbcUrl, username, password, schema):
        self.schema = schema

        # Parse jdbc url
        # Postgres template: jdbc:postgresql://localhost:5432/dspace
        # Oracle template: jdbc:oracle:thin:@//localhost:1521/xe
        m = re.match("^jdbc:(postgresql|oracle):[^\/]*\/\/([^:]+):(\d+)/(.*)$", jdbcUrl)
        if m is None:
            logger.error("Could not parse db.url string: %s" % jdbcUrl)
            raise ValueError

        (engine, hostname, port, database) = m.group(1, 2, 3, 4)

        if engine != "postgresql":
            logger.error("DB Engine not yet supported: %s" % engine)
            raise NotImplementedError

        self.connString = '{engine}://{username}:{password}@{hostname}:{port}/{database}'
        self.connString = self.connString.format(
                engine=engine,
                username=username,
                password=password,
                hostname=hostname,
                port=port,
                database=database,
                )
        logger.debug('DB Connection String: ' + self.connString)
        try:
            self.conn = sqlalchemy.create_engine(self.connString).connect()
            logger.debug('DB Connection established successfully.')
        except sqlalchemy.exc.OperationalError:
            logger.exception("Could not connect to DB.")
            raise


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
        propertiesFilename = "%s/%s.properties" % (args.config_dir, repoName)
        repo = Repository(propertiesFilename)
        eventPipeline = EventPipelineBuilder().build(repo)
        eventPipeline.run()
        logger.debug("END: %s" % repoName)


def parse_args():

    def valid_date_type(arg_date_str):
        """custom argparse *date* type for user dates values given from the command line"""
        # https://gist.github.com/monkut/e60eea811ef085a6540f
        try:
            return datetime.datetime.strptime(arg_date_str, "%Y-%m-%d")
        except ValueError:
            msg = "Given Date ({0}) not valid! Expected format, YYYY-MM-DD!".format(arg_date_str)
            raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("repositories",
                        metavar="<repo_name>",
                        nargs="+",
                        help="name of repositories to collect usage stats from. Should match the name of the corresponding properties files in config dir")
    parser.add_argument("-f", "--date_from",
                        type=valid_date_type,
                        metavar="<YYYY-MM-DD>",
                        default=None,
                        help="collect events only from this date")
    parser.add_argument("-l",
                        "--limit",
                        metavar="<n>",
                        type=int,
                        help="max number of events to output")
    parser.add_argument("-c",
                        "--config_dir",
                        metavar="<dir>",
                        default="./config",
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
        loglevel = logging.INFO

    main(args, loglevel)

