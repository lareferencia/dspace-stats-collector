#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Main / Command line tool """

import logging
logger = logging.getLogger()

class DSpaceDBFilter:

    def __init__(self, configContext):
        self._db = configContext.db

    def run(self, events):
        for event in events:
            resourceId = event._src['id']
            if event._src['type'] == 0: # Download
                isDownload = True
                owningItem = event._src['owningItem']
                event._db = self._db.queryDownload(resourceId, owningItem)
            elif event._src['type'] == 2: # Item
                isDownload = False
                owningItem = None
                event._db = self._db.queryItem(resourceId)
            else:
                logger.error("Unexpected resource type {} for resource: {}".format(event._src['type'], event._src))
                raise ValueError
            if event._db is None:
                logger.warning("Dropping event due db error on data recovery: {}".format(event._src))
                continue # Drop event if could not recover data from db
            yield event