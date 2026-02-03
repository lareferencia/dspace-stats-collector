#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke tests for configure CLI behavior."""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from dspace_stats_collector import configure
from dspace_stats_collector.configcontext import ConfigurationContext


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def test_configure_main_creates_config_and_counter_robots(tmp_path):
    config_dir = tmp_path / "config"
    args = Namespace(repository="repo", config_dir=str(config_dir), verbose=False)
    robots_payload = b'[{"pattern": "bot"}]'

    with patch("dspace_stats_collector.configure.parse_args", return_value=args):
        with patch("urllib.request.urlopen", return_value=_FakeResponse(robots_payload)):
            configure.main()

    props_file = config_dir / "repo.properties"
    robots_file = config_dir / ConfigurationContext.counterRobotsFileName

    assert props_file.exists()
    assert robots_file.exists()
    assert "dspace.majorVersion = 6" in props_file.read_text(encoding="utf-8")
    assert robots_file.read_bytes() == robots_payload
