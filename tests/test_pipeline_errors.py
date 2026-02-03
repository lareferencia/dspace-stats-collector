#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for pipeline error handling."""

import pytest

from dspace_stats_collector.eventpipeline import Event, EventPipeline


class _InputStage:
    def run(self):
        event = Event()
        event._id = 1
        yield event


class _PassThroughFilter:
    def run(self, events):
        yield from events


class _FailingOutput:
    def run(self, events):
        list(events)
        raise RuntimeError("boom")


def test_event_pipeline_propagates_output_errors():
    pipeline = EventPipeline(_InputStage(), [_PassThroughFilter()], _FailingOutput())

    with pytest.raises(RuntimeError, match="boom"):
        pipeline.run()
