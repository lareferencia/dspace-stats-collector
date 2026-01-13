#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DSpace DB Filter.

Enriches events with metadata from the DSpace database.
"""

import logging
from typing import List, Iterator, Optional

try:
    from .eventpipeline import Event, PipelineFilter
except ImportError:
    from eventpipeline import Event, PipelineFilter

logger = logging.getLogger(__name__)


BATCH_SIZE = 50


class DSpaceDBFilter(PipelineFilter):
    """
    Enriches usage events with metadata (title, handle, filenames) 
    queried from the DSpace database.
    """

    def __init__(self, config_context) -> None:
        self._db = config_context.db
        self._batch_size = BATCH_SIZE

    def run(self, events: Iterator[Event]) -> Iterator[Event]:
        """
        Process events in batches to allow for database prefetching.
        """
        buffer: List[Event] = []

        for event in events:
            buffer.append(event)
            if len(buffer) >= self._batch_size:
                yield from self._process_batch(buffer)
                buffer = []
        
        # Process remaining events
        if buffer:
            yield from self._process_batch(buffer)

    def _process_batch(self, events: List[Event]) -> Iterator[Event]:
        """Process a batch of events."""
        # Future optimization: self._db.prefetch(events)
        
        for event in events:
            resource_id = event._src['id']
            event_type = event._src['type']

            try:
                if event_type == 0:  # Download
                    event_db = self._db.queryDownload(resource_id)
                elif event_type == 2:  # Item
                    event_db = self._db.queryItem(resource_id)
                else:
                    logger.warning(
                        "Unexpected resource type %s for resource: %s", 
                        event_type, event._src
                    )
                    continue

                if event_db is None:
                    logger.debug(
                        "Dropping event - data not found in DB: %s", 
                        event._src
                    )
                    continue

                event._db = event_db
                logger.debug('DSPACE_DB_FILTER:: Event enriched: %s', event._id)
                yield event

            except Exception as e:
                logger.error(
                    "Error processing event %s: %s", 
                    event._src.get('id'), e
                )
                continue