#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke tests for collector CLI parsing and failure paths."""

import logging
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from dspace_stats_collector import collector
from dspace_stats_collector.matomooutput import MatomoOfflineException


def test_parse_args_accepts_valid_dates(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["collector.py", "-f", "2026-01-13", "-u", "2026-01-31"],
    )

    args = collector.parse_args()

    assert args.date_from.strftime("%Y-%m-%d") == "2026-01-13"
    assert args.date_until.strftime("%Y-%m-%d") == "2026-01-31"


def test_parse_args_rejects_invalid_date(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["collector.py", "-f", "2026-99-99"])

    with pytest.raises(SystemExit):
        collector.parse_args()


def test_run_exits_when_configuration_fails():
    args = SimpleNamespace(
        repository="repo",
        date_from=None,
        date_until=None,
        config_dir="/tmp/config",
        verbose=False,
        debug=False,
        archived_core=None,
    )

    with patch("dspace_stats_collector.collector.parse_args", return_value=args):
        with patch("dspace_stats_collector.collector.os.path.exists", return_value=True):
            with patch("dspace_stats_collector.collector.logging.FileHandler", return_value=logging.NullHandler()):
                with patch("dspace_stats_collector.collector.ConfigurationContext", side_effect=Exception("bad config")):
                    with patch("dspace_stats_collector.collector.sys.exit", side_effect=SystemExit(1)) as mock_exit:
                        with pytest.raises(SystemExit):
                            collector.run()

    mock_exit.assert_called_once_with(1)


def test_run_handles_matomo_offline_and_closes_context():
    args = SimpleNamespace(
        repository="repo",
        date_from=None,
        date_until=None,
        config_dir="/tmp/config",
        verbose=False,
        debug=False,
        archived_core=None,
    )
    mock_context = MagicMock()
    mock_context.history.get_last_tracked_timestamp.return_value = "2026-01-13T00:00:00.000000Z"
    mock_pipeline = MagicMock()
    mock_pipeline.run.side_effect = MatomoOfflineException("offline")

    with patch("dspace_stats_collector.collector.parse_args", return_value=args):
        with patch("dspace_stats_collector.collector.os.path.exists", return_value=True):
            with patch("dspace_stats_collector.collector.logging.FileHandler", return_value=logging.NullHandler()):
                with patch("dspace_stats_collector.collector.ConfigurationContext", return_value=mock_context):
                    with patch("dspace_stats_collector.collector.EventPipelineBuilder.build", return_value=mock_pipeline):
                        collector.run()

    mock_pipeline.run.assert_called_once()
    mock_context.close.assert_called_once()
