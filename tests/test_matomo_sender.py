#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for MatomoBufferedSender transport settings."""

from unittest.mock import MagicMock

from dspace_stats_collector.matomooutput import MatomoBufferedSender


class _ConfigWithoutVerify:
    def getMatomoUrl(self):
        return "https://matomo.example.com/matomo.php"

    def getMatomoTokenAuth(self):
        return "token"

    def getMatomoOutputSize(self):
        return 50


class _ConfigWithVerify(_ConfigWithoutVerify):
    def __init__(self, verify_ssl):
        self._verify_ssl = verify_ssl

    def getMatomoVerifySSL(self):
        return self._verify_ssl


def _mock_success_response():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "success", "invalid": 0}
    return response


def test_sender_uses_ssl_verification_by_default():
    sender = MatomoBufferedSender(_ConfigWithoutVerify())
    sender._session.post = MagicMock(return_value=_mock_success_response())

    sender._send_requests_to_matomo([("?idsite=1", False, "2026-01-01T00:00:00.000Z")])

    assert sender._session.post.call_args.kwargs["verify"] is True


def test_sender_respects_explicit_verify_ssl_setting():
    sender = MatomoBufferedSender(_ConfigWithVerify(False))
    sender._session.post = MagicMock(return_value=_mock_success_response())

    sender._send_requests_to_matomo([("?idsite=1", False, "2026-01-01T00:00:00.000Z")])

    assert sender._session.post.call_args.kwargs["verify"] is False
