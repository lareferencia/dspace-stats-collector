#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Typed configuration settings."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MatomoSettings:
    url: str
    token_auth: str
    site_id: str
    batch_size: int = 50
    rec: str = "1"
    country_iso: Optional[str] = None


@dataclass
class SolrSettings:
    server_url: str
    core_name: str = "statistics"
    query_rows: int = 500
    date_from: Optional[str] = None
    date_until: Optional[str] = None


@dataclass
class DSpaceSettings:
    install_dir: str
    major_version: str
    db_url: str
    db_username: str
    db_password: str
    canonical_prefix: str
    hostname: str
    url: str
    server_url: str
    ui_url: str


@dataclass
class CollectorSettings:
    matomo: MatomoSettings
    solr: SolrSettings
    dspace: DSpaceSettings
    max_events: int = 100
    anonymize_ip_mask: str = "255.255.255.255"
