#!/usr/bin/env python
#
# -*- coding: utf-8 -*-

"""Main module."""
import json
import sys
import argparse
import logging
import datetime


DESCRIPTION = """
Collects Usage Stats from DSpace repositories.
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
        return json.dumps(self._data_dict)


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
            e = Event()
            e.id = "00" + str(x)
            yield e


class DummyFilter:

    def __init__(self):
        None

    def run(self, events):
        #print(events)

        for event in events:
            event.url = "http://dummy.org/" + event.id
            yield event


class DummyOutput:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            print(event.toJSON())


class EventPipelineBuilder:

    def __init__(self, args):
        None

    def build(self, repo):
        return EventPipeline(DummyInput(), [DummyFilter()], DummyOutput())


def main(args, loglevel):

    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)
    logging.debug("Verbose: %s" % args.verbose)
    logging.debug("Source: %s" % args.source)
    logging.debug("Limit: %s" % args.limit)
    if args.datefrom:
        logging.debug("Date from: %s" % args.datefrom.strftime("%Y-%m-%d"))

    epb = EventPipelineBuilder(args)
    for repo in args.source:
        logging.debug("START: %s" % repo)
        pipeline = epb.build(repo)
        pipeline.run()
        logging.debug("END: %s" % repo)


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
    parser.add_argument("source",
                        metavar="R",
                        nargs="+",
                        help="source repositories to collect usage stats from")
    parser.add_argument("-f", "--datefrom",
                        type=valid_date_type,
                        metavar="<YYYY-MM-DD>",
                        default=None,
                        help="collect events only from this date")
    parser.add_argument("-l",
                        "--limit",
                        metavar="<n>",
                        type=int,
                        help="max number of events to output")
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

