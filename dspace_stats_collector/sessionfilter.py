#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

from dateutil import parser as dateutil_parser
from hashlib import md5
from anonymizeip import anonymize_ip


class SimpleHashSessionFilter:

    def __init__(self, configContext):
        self._anonymize_ip_mask = configContext.anonymize_ip_mask


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

            # Anonymize IP
            if self._anonymize_ip_mask != '255.255.255.255':     
                event._src['ip'] = anonymize_ip(event._src['ip'], self._anonymize_ip_mask)    

            logger.debug('SESSION_FILTER:: Event: {} Session string: {}'.format(event._id, srcString))

            yield event