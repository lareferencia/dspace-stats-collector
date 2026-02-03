#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""End-to-end simulation test for the DSpace processing pipeline."""

import json
from copy import deepcopy

from dspace_stats_collector.counterfilter import COUNTERRobotsFilter
from dspace_stats_collector.dspacefilter import DSpaceDBFilter
from dspace_stats_collector.eventpipeline import Event, EventPipeline
from dspace_stats_collector.matomooutput import MatomoFilter, MatomoOutput
from dspace_stats_collector.sessionfilter import SimpleHashSessionFilter


class _FakeInput:
    def __init__(self, docs):
        self._docs = docs

    def run(self):
        for idx, doc in enumerate(self._docs):
            event = Event()
            event._id = idx
            event._src = deepcopy(doc)
            yield event


class _FakeDSpaceDB:
    def __init__(self):
        self.download_calls = 0
        self.item_calls = 0

    def queryDownload(self, resource_id):
        self.download_calls += 1
        if resource_id != "bitstream-1":
            return None
        return {
            "id": resource_id,
            "record_title": "Download test record",
            "handle": "12345/100",
            "is_download": True,
            "sequence_id": 1,
            "filename": "article.pdf",
        }

    def queryItem(self, resource_id):
        self.item_calls += 1
        if resource_id != "item-1":
            return None
        return {
            "id": resource_id,
            "record_title": "Item test record",
            "handle": "12345/101",
            "is_download": False,
            "sequence_id": None,
            "filename": None,
        }


class _FakeHistory:
    def __init__(self):
        self.saved_timestamps = []

    def save_last_tracked_timestamp(self, timestamp):
        self.saved_timestamps.append(timestamp)

    def get_last_tracked_timestamp(self):
        if not self.saved_timestamps:
            return None
        return self.saved_timestamps[-1]


class _FakeMatomoSender:
    def __init__(self, config):
        self._config = config
        self._buffer = []
        self.total_sent = 0
        self.processed_events = []
        self.sent_requests = []

    def send(self, event):
        self.processed_events.append(event)
        self._buffer.append(event)

    def flush(self):
        if not self._buffer:
            return
        self._config.history.save_last_tracked_timestamp(self._buffer[-1]._src['time'])
        for event in self._buffer:
            if not event.is_robot:
                self.total_sent += 1
                self.sent_requests.append(event._matomoRequest)
        self._buffer = []


class _FakeConfig:
    def __init__(self, counter_robots_file):
        self.db = _FakeDSpaceDB()
        self.anonymize_ip_mask = "255.255.255.255"
        self.counterRobotsFilename = counter_robots_file
        self.dspaceMajorVersion = "6"
        self.solrQueryInitialTimestamp = "2026-01-13T00:00:00.000Z"
        self.history = _FakeHistory()
        self.dspaceProperties = {
            "handle.canonical.prefix": "http://hdl.handle.net/",
            "dspace.hostname": "dspace.example.org",
            "dspace.url": "http://dspace.example.org",
            "dspace.server.url": "http://api.dspace.example.org",
            "dspace.ui.url": "http://dspace.example.org",
        }
        self.properties = {
            "matomo.idSite": "1",
            "matomo.rec": "1",
            "matomo.repositoryId": "repo-1",
            "matomo.countryISO": "US",
            "matomo.token_auth": "token",
        }

    def getDspaceMajorVersion(self):
        return "6"

    def getMatomoUrl(self):
        return "https://matomo.example.org/matomo.php"

    def getMatomoTokenAuth(self):
        return self.properties["matomo.token_auth"]

    def getMatomoOutputSize(self):
        return 50

    def getMatomoVerifySSL(self):
        return True


def test_simulated_dspace_pipeline_processes_all_steps(tmp_path):
    counter_file = tmp_path / "COUNTER_Robots_list.json"
    counter_file.write_text(json.dumps([{"pattern": "(?i)bot"}]), encoding="utf-8")

    docs = [
        {
            "id": "bitstream-1",
            "type": 0,
            "time": "2026-01-13T12:00:00.000Z",
            "ip": "192.168.10.50",
            "userAgent": "Mozilla/5.0",
            "referrer": "https://example.org",
        },
        {
            "id": "item-1",
            "type": 2,
            "time": "2026-01-13T13:30:45Z",
            "ip": "192.168.10.99",
            "userAgent": "Googlebot/2.1",
        },
        # Unexpected type, should be discarded by DSpaceDBFilter.
        {
            "id": "ignored-1",
            "type": 99,
            "time": "2026-01-13T15:00:00.000Z",
            "ip": "10.0.0.8",
            "userAgent": "curl/8.0",
        },
    ]

    config = _FakeConfig(str(counter_file))
    output = MatomoOutput(config)
    output._sender = _FakeMatomoSender(config)
    pipeline = EventPipeline(
        _FakeInput(docs),
        [
            COUNTERRobotsFilter(config),
            DSpaceDBFilter(config),
            SimpleHashSessionFilter(config),
            MatomoFilter(config),
        ],
        output,
    )

    pipeline.run()

    assert config.db.download_calls == 1
    assert config.db.item_calls == 1
    assert len(output._sender.processed_events) == 2
    assert len(output._sender.sent_requests) == 1
    assert output._sender.total_sent == 1
    assert config.history.get_last_tracked_timestamp() == "2026-01-13T13:30:45Z"

    by_id = {event._src["id"]: event for event in output._sender.processed_events}
    assert set(by_id.keys()) == {"bitstream-1", "item-1"}

    download_event = by_id["bitstream-1"]
    item_event = by_id["item-1"]

    assert download_event.is_robot is False
    assert item_event.is_robot is True
    assert download_event._sess["id"]
    assert item_event._sess["id"]
    assert download_event._matomoRequest.startswith("?")
    assert item_event._matomoRequest.startswith("?")

    assert "download" in download_event._matomoParams
    assert "article.pdf" in download_event._matomoParams["download"]
    assert "download" not in item_event._matomoParams
    assert item_event._matomoParams["url"] == "http://hdl.handle.net/12345/101"
