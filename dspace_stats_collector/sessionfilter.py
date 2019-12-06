#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

from dateutil import parser as dateutil_parser
from hashlib import md5


class SimpleHashSessionFilter:

    def __init__(self, configContext):
        None

    def run(self, events):
        for event in events:
            srcString = "{:%Y-%m-%d}#{}#{}".format(
                            dateutil_parser.parse(event._src['time']),
                            event._src['ip'],
                            event._src['userAgent']
                        )
            sessDict = {
                        'id': md5(srcString.encode()).hexdigest(),
                        'srcString': srcString
                       }
            event._sess = sessDict
            yield event