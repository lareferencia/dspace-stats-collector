#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `dspace_stats_collector` package."""

import pytest


from dspace_stats_collector import dspace_stats_collector


# @pytest.fixture
# def response():
#     """Sample pytest fixture.

#     See more at: http://doc.pytest.org/en/latest/fixture.html
#     """
#     # import requests
#     # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')

def test_dummy_pipeline():
     dspace_stats_collector.dummy_pipeline.run()