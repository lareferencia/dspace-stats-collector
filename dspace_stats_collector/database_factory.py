#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Factory for DSpace.

Provides a factory function to create the appropriate database connector
based on the DSpace version, eliminating the need for version-specific
imports in ConfigurationContext.
"""

import logging
from typing import Literal

from .dspacedb import DSpaceDB
from .queries import get_queries

logger = logging.getLogger(__name__)


# Type alias for supported DSpace versions
DSpaceVersion = Literal['4', '5', '5c', '5o', '6', '6o', '7', '8', '9']


def create_database(
    version: DSpaceVersion,
    jdbc_url: str,
    username: str,
    password: str
) -> DSpaceDB:
    """
    Factory function to create a DSpace database connector.
    
    This replaces the previous approach of importing version-specific
    classes (DSpaceDB4, DSpaceDB5, etc.) with a single factory that
    configures the base DSpaceDB class with the appropriate queries.
    
    Args:
        version: DSpace version string ('4', '5', '5c', '5o', '6', '6o', '7')
        jdbc_url: JDBC connection URL
        username: Database username
        password: Database password
        
    Returns:
        Configured DSpaceDB instance
        
    Raises:
        KeyError: If version is not supported
    """
    queries = get_queries(version)
    
    logger.info("Creating database connector for DSpace version: %s", version)
    
    db = DSpaceDB(jdbc_url, username, password)
    
    # Configure queries
    db._queryDownloadSQL = queries.download
    db._queryItemSQL = queries.item
    db._queryTitleSQL = queries.title
    
    # Initialize title ID
    db._dcTitleId = db.getDcTitleId()
    
    return db
