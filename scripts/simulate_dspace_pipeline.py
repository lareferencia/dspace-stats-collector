#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simulate all collector stages from Solr input to Matomo output."""

import json
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

# Allow running the script directly from the repository checkout.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dspace_stats_collector.counterfilter import COUNTERRobotsFilter
from dspace_stats_collector.dspacefilter import DSpaceDBFilter
from dspace_stats_collector.eventpipeline import Event
from dspace_stats_collector.matomooutput import MatomoFilter, MatomoOutput
from dspace_stats_collector.sessionfilter import SimpleHashSessionFilter


class FakeDSpaceDB:
    """In-memory DB simulator for queryDownload/queryItem calls."""

    def __init__(self):
        self._download_records = {
            "bitstream-1": {
                "id": "bitstream-1",
                "record_title": "How to share open science data",
                "handle": "12345/100",
                "is_download": True,
                "sequence_id": 1,
                "filename": "open-science.pdf",
            }
        }
        self._item_records = {
            "item-1": {
                "id": "item-1",
                "record_title": "Repository landing page",
                "handle": "12345/101",
                "is_download": False,
                "sequence_id": None,
                "filename": None,
            }
        }

    def queryDownload(self, resource_id):
        return self._download_records.get(resource_id)

    def queryItem(self, resource_id):
        return self._item_records.get(resource_id)


class FakeHistory:
    def __init__(self):
        self._last = None

    def save_last_tracked_timestamp(self, timestamp):
        self._last = timestamp

    def get_last_tracked_timestamp(self):
        return self._last


class FakeMatomoSender:
    """Captures what would be sent to Matomo without network traffic."""

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


class FakeConfigContext:
    """Small config stub compatible with the existing filters."""

    def __init__(self, counter_robots_filename):
        self.db = FakeDSpaceDB()
        self.anonymize_ip_mask = "255.255.255.255"
        self.counterRobotsFilename = counter_robots_filename
        self.dspaceMajorVersion = "6"
        self.solrQueryInitialTimestamp = "2026-01-13T00:00:00.000Z"
        self.history = FakeHistory()
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
            "matomo.token_auth": "token-123",
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


def build_solr_docs():
    """Fake Solr payload that mimics what SolrStatisticsInput yields."""
    return [
        {
            "id": "bitstream-1",
            "type": 0,
            "time": "2026-01-13T12:00:00.000Z",
            "ip": "192.168.10.50",
            "userAgent": "Mozilla/5.0",
            "referrer": "https://www.google.com",
        },
        {
            "id": "item-1",
            "type": 2,
            "time": "2026-01-13T13:30:45Z",
            "ip": "192.168.10.99",
            "userAgent": "Googlebot/2.1",
        },
        {
            "id": "ignored-1",
            "type": 99,
            "time": "2026-01-13T15:00:00.000Z",
            "ip": "10.0.0.8",
            "userAgent": "curl/8.0",
        },
    ]


def docs_to_events(docs):
    events = []
    for idx, doc in enumerate(docs):
        event = Event()
        event._id = idx
        event._src = deepcopy(doc)
        events.append(event)
    return events


def snapshot_event(event):
    return {
        "_id": event._id,
        "_src": event._src,
        "_db": event._db,
        "_sess": event._sess,
        "_matomoParams": event._matomoParams,
        "_matomoRequest": event._matomoRequest,
        "is_robot": event.is_robot,
    }


def print_stage(title, events):
    print("")
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(f"Eventos en esta etapa: {len(events)}")
    for event in events:
        print(json.dumps(snapshot_event(event), indent=2, ensure_ascii=True))


def print_output_stage(output):
    print("")
    print("=" * 80)
    print("6) Salida Matomo (simulada, sin red)")
    print("=" * 80)
    print(f"Eventos procesados por output: {len(output._sender.processed_events)}")
    print(f"Eventos enviados (no robot): {output._sender.total_sent}")
    print(f"Ultimo timestamp guardado en history: {output._config_context.history.get_last_tracked_timestamp()}")
    print("Requests que se enviarian a Matomo:")
    for req in output._sender.sent_requests:
        print(req)


def create_counter_robots_file():
    with NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([{"pattern": "(?i)bot"}], f)
        return f.name


def main():
    counter_file = create_counter_robots_file()
    config = FakeConfigContext(counter_file)
    docs = build_solr_docs()

    events = docs_to_events(docs)
    print_stage("1) Entrada desde Solr (simulada)", events)

    events = list(COUNTERRobotsFilter(config).run(events))
    print_stage("2) Filtro COUNTER robots (marca is_robot)", events)

    events = list(DSpaceDBFilter(config).run(events))
    print_stage("3) Enriquecidos desde DSpace DB (simulada)", events)

    events = list(SimpleHashSessionFilter(config).run(events))
    print_stage("4) Con sesion calculada (SimpleHashSessionFilter)", events)

    events = list(MatomoFilter(config).run(events))
    print_stage("5) Transformados a payload de Matomo (MatomoFilter)", events)

    output = MatomoOutput(config)
    output._sender = FakeMatomoSender(config)
    output.run(events)
    print_output_stage(output)

    print("")
    print("Listo. Simulacion completa de todos los pasos del pipeline.")


if __name__ == "__main__":
    main()
