"""Regression coverage for helpdesk issue #200."""
import json
import re
from unittest.mock import MagicMock

import pytest
import requests

from dspace_stats_collector.eventpipeline import Event
from dspace_stats_collector.matomooutput import MatomoBufferedSender, MatomoOfflineException
from dspace_stats_collector.solrinput import SolrTimestampCursor

START = '2023-05-05T07:31:29.546Z'
END = '2026-01-01T00:00:00.000Z'
DOCS = [{'time': '2025-01-01T00:00:00.000Z'},
        {'time': '2025-06-01T00:00:00.000Z'}]


class Solr:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def _select(self, query):
        self.queries.append(query)
        lower, upper = re.search(r'time:\{"(.*?)" TO "(.*?)"\]', query['q']).groups()
        docs = [d for d in self.docs if lower < d['time'] <= upper]
        return json.dumps({'response': {'docs': docs[:query['rows']]}})


def test_crosses_multi_year_and_inter_page_gaps():
    solr = Solr(DOCS)
    pages = list(SolrTimestampCursor(solr, {}).fetch(
        rows=1, initialTimestamp=START, untilDate=END))
    assert pages == [[DOCS[0]], [DOCS[1]]]
    assert len(solr.queries) == 3


def test_empty_range_finishes_in_one_request():
    solr = Solr([])
    assert list(SolrTimestampCursor(solr, {}).fetch(initialTimestamp=START)) == []
    assert len(solr.queries) == 1


def test_limit_and_until_are_respected():
    solr = Solr(DOCS)
    assert list(SolrTimestampCursor(solr, {}).fetch(
        limit=1, initialTimestamp=START, untilDate=END)) == [[DOCS[0]]]
    assert len(solr.queries) == 1
    assert list(SolrTimestampCursor(Solr(DOCS), {}).fetch(
        initialTimestamp=START, untilDate='2024-01-01T00:00:00.000Z')) == []


def test_failed_delivery_after_gap_is_read_again(mock_config_context):
    config = mock_config_context
    config.getMatomoOutputSize.return_value = 1
    config.history.save_last_tracked_timestamp = MagicMock()
    first_page = next(SolrTimestampCursor(Solr(DOCS), {}).fetch(
        initialTimestamp=START, untilDate=END))
    event = Event()
    event._src = first_page[0]
    event._matomoRequest = '?idsite=1'
    event.is_robot = False
    with MatomoBufferedSender(config) as sender:
        sender._session.post = MagicMock(side_effect=requests.ConnectionError('offline'))
        with pytest.raises(MatomoOfflineException):
            sender.send(event)
    config.history.save_last_tracked_timestamp.assert_not_called()
    repeated = next(SolrTimestampCursor(Solr(DOCS), {}).fetch(
        initialTimestamp=START, untilDate=END))
    assert repeated == first_page
    with MatomoBufferedSender(config) as sender:
        response = MagicMock()
        response.json.return_value = {'status': 'success', 'invalid': 0}
        sender._session.post = MagicMock(return_value=response)
        sender.send(event)
    config.history.save_last_tracked_timestamp.assert_called_once_with(DOCS[0]['time'])
