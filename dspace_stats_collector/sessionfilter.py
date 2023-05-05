#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

from dateutil import parser as dateutil_parser
from hashlib import md5
from anonymizeip import anonymize_ip
from ipaddress import ip_address


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


            try:
                # Anonymize IP
                if self._anonymize_ip_mask != self.FULL_IP_MASK:     
                    event._src['ip'] = anonymize_ip(event._src.get('ip','0.0.0.0'), self._anonymize_ip_mask)    
            
            except Exception as e:

                 # check if ip is folowing the format ip:port
                if ':' in event._src.get('ip','0.0.0.0'):

                    splited = event._src.get('ip','0.0.0.0').split(':')

                    if len(splited) > 1:
                        ip = splited[0]
                    else:
                        ip = '0.0.0.0'
                    
                    ## check the ip string is a valid ip address
                    try:
                        # this will raise a ValueError if the ip is not valid
                        ip_address(ip)

                        # anonymize ip
                        event._src['ip'] = anonymize_ip(ip, self._anonymize_ip_mask)

                    except ValueError:
                        logger.error("Error anonymizing parsed IP from XXXX:port pattern: {}".format(e))         
                        event._src['ip'] = '0.0.0.0'
                        
                else:
                    logger.error("Error anonymizing IP: {}".format(e))
                    event._src['ip'] = '0.0.0.0'

            logger.debug('SESSION_FILTER:: Event: {} Session string: {}'.format(event._id, srcString))

            yield event