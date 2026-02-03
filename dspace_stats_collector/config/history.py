#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""History state management."""

import logging
import os
from datetime import datetime
from pyjavaprops.javaproperties import JavaProperties

logger = logging.getLogger(__name__)

TIMESTAMP_PATTERN = "%Y-%m-%dT%H:%M:%S.%fZ"
LAST_TRACKED_TIMESTAMP_HISTORY_FIELD = 'lastTrackedEventTimestamp'


class History:
    """Manages the persistent state of the last tracked event timestamp."""

    def __init__(self, base_path, reponame):
        self.javaprops = JavaProperties()
        self.base_path = base_path
        self.reponame = reponame
        self.property_dict = {LAST_TRACKED_TIMESTAMP_HISTORY_FIELD: None}
        self.filename = "{}/{}".format(base_path, reponame + ".dat")

        try:
            with open(self.filename) as f:
                self.javaprops.load(f)
            self.property_dict = self.javaprops.get_property_dict()
            logger.debug("Read successfully history file %s" % self.filename)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("History file %s does not exist. Creating one..." % self.filename)

    def save_last_tracked_timestamp(self, timestamp):
        try:
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path)
            
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime(TIMESTAMP_PATTERN)
            else:
                timestamp_str = timestamp # Assume it's already a string in the correct format

            self.javaprops.set_property(LAST_TRACKED_TIMESTAMP_HISTORY_FIELD, timestamp_str)    
            with open(self.filename, mode='w') as f:
                self.javaprops.store(f)
            self.property_dict = self.javaprops.get_property_dict()    
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not save to history file %s" % self.filename)
            raise

    def get_last_tracked_timestamp(self):
        timestamp_str = self.property_dict.get(LAST_TRACKED_TIMESTAMP_HISTORY_FIELD, None)
        if timestamp_str:
            possible_formats = [
                TIMESTAMP_PATTERN,                # "%Y-%m-%dT%H:%M:%S.%fZ"
                "%Y-%m-%dT%H:%M:%S.%f",           # Without Z
                "%Y-%m-%dT%H:%M:%SZ",             # ISO 8601 no millis
                "%Y-%m-%dT%H:%M:%S",              # ISO 8601 no millis no Z
                "%Y-%m-%d %H:%M:%S.%f",           # Space + millis
                "%Y-%m-%d %H:%M:%S"               # Space no millis
            ]
            
            dt_object = None
            for fmt in possible_formats:
                try:
                    dt_object = datetime.strptime(timestamp_str, fmt)
                    break 
                except ValueError:
                    continue
            
            if dt_object:
                return dt_object.strftime(TIMESTAMP_PATTERN)
            else:
                logger.error(
                    "Error parsing stored timestamp: '%s'. Tried formats: %s.",
                    timestamp_str,
                    possible_formats
                )
                raise ValueError(
                    f"Could not parse timestamp string '{timestamp_str}'"
                )
        return None
