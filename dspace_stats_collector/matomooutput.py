#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Matomo pipeline components.

This module handles the transformation of events into Matomo tracking format
and sending them to the Matomo server.
"""

import logging
import urllib.parse
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Tuple, Iterator, Optional

from pytz import timezone
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

try:
    from .eventpipeline import Event, PipelineFilter, PipelineOutput
except ImportError:
    from eventpipeline import Event, PipelineFilter, PipelineOutput

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class MatomoException(Exception):
    """Base class for Matomo-related exceptions."""
    pass


class MatomoOfflineException(MatomoException):
    """Raised when Matomo server is unreachable."""
    pass


class MatomoInternalServerException(MatomoException):
    """Raised when Matomo returns an error response."""
    pass


# =============================================================================
# MatomoFilter - Transform events to Matomo format
# =============================================================================

class MatomoFilter(PipelineFilter):
    """
    Transforms events into Matomo tracking API format.
    
    Adds _matomoParams and _matomoRequest attributes to each event.
    """

    def __init__(self, config_context) -> None:
        dspace_properties = getattr(config_context, "dspaceProperties", None)
        if not isinstance(dspace_properties, dict):
            settings = getattr(config_context, "settings", None)
            dspace_settings = getattr(settings, "dspace", None)
            dspace_properties = {
                'handle.canonical.prefix': getattr(dspace_settings, 'canonical_prefix', 'http://hdl.handle.net/'),
                'dspace.hostname': getattr(dspace_settings, 'hostname', None),
                'dspace.url': getattr(dspace_settings, 'url', None),
                'dspace.server.url': getattr(dspace_settings, 'server_url', None),
                'dspace.ui.url': getattr(dspace_settings, 'ui_url', None),
            }

        self._handle_canonical_prefix = dspace_properties.get(
            'handle.canonical.prefix', 
            'http://hdl.handle.net/'
        )
            
        if config_context.getDspaceMajorVersion() == '7':
            self._dspace_hostname = dspace_properties['dspace.server.url']
            self._dspace_url = dspace_properties['dspace.ui.url']
        else:
            self._dspace_hostname = dspace_properties['dspace.hostname']
            self._dspace_url = dspace_properties['dspace.url']

        repo_properties = getattr(config_context, "properties", None)
        if not isinstance(repo_properties, dict):
            settings = getattr(config_context, "settings", None)
            matomo_settings = getattr(settings, "matomo", None)
            repo_properties = {
                'matomo.idSite': getattr(matomo_settings, 'site_id', None),
                'matomo.rec': getattr(matomo_settings, 'rec', "1"),
                'matomo.repositoryId': getattr(matomo_settings, 'repository_id', None),
                'matomo.countryISO': getattr(matomo_settings, 'country_iso', None),
                'matomo.token_auth': getattr(matomo_settings, 'token_auth', None),
            }
        self._repo_properties = repo_properties

    def run(self, events: Iterator[Event]) -> Iterator[Event]:
        """Transform events to Matomo tracking format."""
        for event in events:
            params = self._build_params(event)
            event._matomoParams = params
            event._matomoRequest = '?' + urllib.parse.urlencode(params)
            
            logger.debug('MATOMO_FILTER:: Event: %s is_robot %s', event._id, event.is_robot)
            yield event

    def _build_params(self, event: Event) -> Dict[str, Any]:
        """Build Matomo tracking parameters from event."""
        params = {
            'idsite': self._repo_properties.get('matomo.idSite'),
            'rec': self._repo_properties.get('matomo.rec', "1"),
            'action_name': event._db['record_title'],
            '_id': event._sess['id'],
            'rand': random.randint(100000, 1000000),
            'apiv': 1,
            'ua': event._src['userAgent'],
            'token_auth': self._repo_properties.get('matomo.token_auth'),
            'cip': event._src.get('ip', '0.0.0.0'),
        }

        # Optional referrer
        if 'referrer' in event._src:
            params['urlref'] = event._src['referrer']

        # OAI-PMH identifier
        oai_id = f"oai:{self._dspace_hostname}:{event._db['handle']}"
        params['cvar'] = json.dumps({
            "1": ["oaipmhID", oai_id],
            "2": ["repositoryID", self._repo_properties.get('matomo.repositoryId', '')],
            "3": ["countryID", self._repo_properties.get('matomo.countryISO', '')]
        })

        # URL based on type (download vs view)
        if event._db['is_download']:
            download_url = f"{self._dspace_url}/bitstream/{event._db['handle']}/{event._db['sequence_id']}/{urllib.parse.quote(event._db['filename'])}"
            params['download'] = download_url
            params['url'] = download_url
        else:
            params['url'] = self._handle_canonical_prefix + event._db['handle']

        # Parse and format timestamp
        params['cdt'] = self._format_timestamp(event._src['time'])

        return params

    def _format_timestamp(self, src_time: str) -> str:
        """Parse Solr timestamp and convert to Matomo format."""
        parsed = None
        # Parse with or without milliseconds
        try:
            parsed = datetime.strptime(src_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                parsed = datetime.strptime(src_time, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                # Fallback for other formats if necessary, or let it fail
                pass
        
        if parsed:
            # Solr times ending in Z are UTC. 
            # Force UTC timezone if naive (which strptime produces)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone('UTC'))
            
            # Convert to target UTC (no-op if already UTC, but safe)
            utc_time = parsed.astimezone(timezone('UTC'))
        else:
            # Fallback if parsing failed (should handle gracefully)
            logger.warning("Could not parse timestamp: %s", src_time)
            # Default to now? Or raw?
            utc_time = datetime.now(timezone('UTC'))

        formatted = datetime.strftime(utc_time, "%Y-%m-%d %H:%M:%S")
        logger.debug('SOLR time %s converted to UTC: %s', src_time, formatted)
        return formatted


# =============================================================================
# MatomoBufferedSender - Batched HTTP sender with retries
# =============================================================================

BULK_TRACKING_BATCH_SIZE_DEFAULT = 50


class MatomoBufferedSender:
    """
    Buffered sender for Matomo tracking events.
    
    Features:
    - HTTP session reuse for better performance
    - Batched sending (configurable batch size)
    - Automatic retry with exponential backoff
    - Fallback to individual event sending on bulk errors
    """

    def __init__(self, config_context) -> None:
        self._config_context = config_context
        self._buffer: List[Tuple[str, bool, str]] = []
        self._total_sent: int = 0
        self._url: str = config_context.getMatomoUrl()
        self._token_auth: str = config_context.getMatomoTokenAuth()
        try:
            self._verify_ssl = bool(config_context.getMatomoVerifySSL())
        except AttributeError:
            self._verify_ssl = True
        
        # HTTP session for connection reuse
        self._session: requests.Session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DSpaceStatsCollector/1.0'
        })
        
        # Buffer size
        try:
            self._buffer_size = config_context.getMatomoOutputSize()
            assert self._buffer_size > 0
        except (AttributeError, AssertionError):
            self._buffer_size = BULK_TRACKING_BATCH_SIZE_DEFAULT

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
        logger.debug("Matomo HTTP session closed")

    @property
    def total_sent(self) -> int:
        return self._total_sent

    # Legacy property name for backward compatibility
    def getTotalSent(self) -> int:
        return self._total_sent

    def send(self, event: Event) -> None:
        """Add event to buffer and flush if full."""
        self._buffer.append((event._matomoRequest, event.is_robot, event._src['time']))
        logger.debug("Event buffered: %s", event.toJSON())
        
        if self._is_buffer_full():
            logger.debug("Buffer full (%d events), flushing", len(self._buffer))
            self.flush()

    def _is_buffer_full(self) -> bool:
        return len(self._buffer) >= self._buffer_size

    # Legacy method name
    def isBufferFull(self) -> bool:
        return self._is_buffer_full()

    @retry(
        retry=retry_if_exception_type(requests.exceptions.Timeout),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _send_requests_to_matomo(
        self, 
        events: List[Tuple[str, bool, str]]
    ) -> Optional[str]:
        """
        Send events to Matomo with retry logic.
        
        Args:
            events: List of (request, is_robot, timestamp) tuples
            
        Returns:
            Last event timestamp if successful
        """
        last_timestamp = events[-1][2] if events else None
        request_list = [m for (m, r, t) in events if not r]  # Exclude robots
        
        if not request_list:
            logger.debug("No non-robot events to send")
            return last_timestamp

        self._total_sent += len(request_list)

        try:
            payload = {
                'requests': request_list,
                'token_auth': self._token_auth
            }
            
            response = self._session.post(
                self._url,
                data=json.dumps(payload),
                timeout=30,
                verify=self._verify_ssl
            )
            response.raise_for_status()
            
            json_response = response.json()
            
            if json_response.get('status') != "success" or json_response.get('invalid', 0) != 0:
                raise MatomoInternalServerException(
                    f"Matomo error: {response.text}"
                )
                
            logger.debug("Successfully sent %d events to Matomo", len(request_list))

        except requests.exceptions.HTTPError as e:
            raise MatomoInternalServerException(str(e))
        except requests.exceptions.ConnectionError as e:
            raise MatomoOfflineException(f"Connection error: {e}")
        except requests.exceptions.Timeout as e:
            logger.warning("Request timeout, will retry: %s", e)
            raise
        except requests.exceptions.RequestException as e:
            raise MatomoOfflineException(str(e))

        return last_timestamp

    # Legacy method name
    def _sendRequestsToMatomo(self, url, events):
        return self._send_requests_to_matomo(events)

    def flush(self) -> None:
        """Flush buffer, sending all events to Matomo."""
        if not self._buffer:
            return

        last_timestamp = None

        try:
            last_timestamp = self._send_requests_to_matomo(self._buffer)

        except MatomoOfflineException:
            raise  # Can't recover from offline

        except MatomoInternalServerException as e:
            logger.error(
                'Matomo error in bulk mode, retrying individually: %s', e
            )
            last_timestamp = self._send_individual_events()

        # Save progress
        if last_timestamp:
            self._config_context.history.save_last_tracked_timestamp(last_timestamp)

        self._buffer = []

    def _send_individual_events(self) -> Optional[str]:
        """Fallback: send events one by one when bulk fails."""
        last_timestamp = None
        
        for (request, is_robot, timestamp) in self._buffer:
            try:
                last_timestamp = timestamp
                if not is_robot:
                    self._send_requests_to_matomo([(request, is_robot, timestamp)])
                    
            except MatomoOfflineException:
                raise
            except MatomoInternalServerException as e:
                logger.error(
                    'Discarding event after retry failure: %s\nRequest: %s',
                    e, request[:200]
                )
                
        return last_timestamp


# =============================================================================
# MatomoOutput - Pipeline output stage
# =============================================================================

class MatomoOutput(PipelineOutput):
    """
    Pipeline output that sends events to Matomo.
    
    Implements the PipelineOutput interface.
    """

    def __init__(self, config_context) -> None:
        self._config_context = config_context
        self._sender = MatomoBufferedSender(config_context)

    def run(self, events: Iterator[Event]) -> None:
        """Process all events and send to Matomo."""
        processed = 0
        robot_count = 0

        for event in events:
            processed += 1
            self._sender.send(event)
            if event.is_robot:
                robot_count += 1

        # Flush remaining events
        logger.debug('Force flushing %d remaining events', len(self._sender._buffer))
        self._sender.flush()

        # Summary log
        logger.info(
            'DSpace Stats Collector finished: %d events processed from %s to %s. '
            'Sent: %d, Robots: %d',
            processed,
            self._config_context.solrQueryInitialTimestamp,
            self._config_context.history.get_last_tracked_timestamp(),
            self._sender.total_sent,
            robot_count
        )
