#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

from dateutil import parser as dateutil_parser
from hashlib import md5
from anonymizeip import anonymize_ip


class SimpleHashSessionFilter:

    FULL_IP_MASK = '255.255.255.255'

    def __init__(self, configContext):
        self._anonymize_ip_mask = configContext.anonymize_ip_mask


    def run(self, events):
        for event in events:
            srcString = "{:%Y-%m-%d}#{}#{}".format(
                            dateutil_parser.parse(event._src['time']),
                            event._src.get('ip', '0.0.0.0'),
                            event._src.get('userAgent', None)
                        )
            sessDict = {
                        'id': md5(srcString.encode()).hexdigest(),
                        'srcString': srcString
                       }
            event._sess = sessDict

            # Anonymize IP
            if self._anonymize_ip_mask != self.FULL_IP_MASK:     
                event._src['ip'] = anonymize_ip(event._src.get('ip','0.0.0.0'), self._anonymize_ip_mask)    

            logger.debug('SESSION_FILTER:: Event: {} Session string: {}'.format(event._id, srcString))

            yield event