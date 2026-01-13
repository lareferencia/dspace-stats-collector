#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" DSpace DB components """

import logging
from typing import Dict, Optional, Any

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
import re
import pandas as pd

logger = logging.getLogger(__name__)


class DSpaceDB:
    """
    Base class for DSpace database connectors.
    
    Provides methods to query item and bitstream information from the DSpace database.
    Uses parameterized queries to prevent SQL injection.
    """

    def __init__(self, jdbc_url: str, username: str, password: str) -> None:
        """
        Initialize database connection.
        
        Args:
            jdbc_url: JDBC connection string (postgres or oracle)
            username: Database username
            password: Database password
        """
        self._engine: Engine = self._create_engine(jdbc_url, username, password)
        self._conn: Connection = self._engine.connect()
        
        # Cache for resource lookups
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        logger.debug('DB Connection established successfully.')

    def _create_engine(self, jdbc_url: str, username: str, password: str) -> Engine:
        """Parse JDBC URL and create SQLAlchemy engine."""
        # Parse jdbc url
        # Postgres template: jdbc:postgresql://localhost:5432/dspace
        # Oracle template: jdbc:oracle:thin:@//localhost:1521/xe
        # Oracle template: jdbc:oracle:thin:@localhost:1521:xe
        pattern = r"^jdbc:(postgresql|oracle):[^\/|^@]*[@\/\/|\/\/|@]*([^:]+):(\d+)(\/|:)(.*)$"
        match = re.match(pattern, jdbc_url)

        if match is None:
            logger.error("Could not parse db.url string: %s", jdbc_url)
            raise ValueError(f"Invalid JDBC URL format: {jdbc_url}")

        engine, hostname, port, separator, database = match.group(1, 2, 3, 4, 5)

        # Build SQLAlchemy connection string
        if engine == 'postgresql':
            conn_string = f'postgresql://{username}:{password}@{hostname}:{port}{separator}{database}'
        elif engine == 'oracle':
            if separator == ':':
                conn_string = f'oracle+cx_oracle://{username}:{password}@{hostname}:{port}/?service_name={database}'
            else:  # separator == '/'
                conn_string = f'oracle+cx_oracle://{username}:{password}@{hostname}:{port}/{database}'
        else:
            raise ValueError(f"Unsupported database engine: {engine}")

        logger.debug('Creating DB engine for: %s@%s:%s/%s', engine, hostname, port, database)
        
        try:
            return sqlalchemy.create_engine(
                conn_string,
                pool_pre_ping=True,  # Verify connection health
                pool_recycle=3600,   # Recycle connections after 1 hour
            )
        except sqlalchemy.exc.OperationalError:
            logger.exception("Could not connect to DB.")
            raise

    def getDcTitleId(self) -> int:
        """Get the metadata field ID for dc.title."""
        result = pd.read_sql(text(self._queryTitleSQL), self._conn)
        if len(result) != 1:
            logger.error('Could not recover DC Title metadata field id from db')
            raise RuntimeError('DC Title field not found in database')
        return int(result.iloc[0]['dcTitleId'])

    def queryDownload(self, bitstream_id: str) -> Optional[Dict[str, Any]]:
        """
        Query download information for a bitstream.
        
        Args:
            bitstream_id: The bitstream identifier
            
        Returns:
            Dictionary with resource info or None if not found
        """
        cache_key = f"download_{bitstream_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use parameterized query to prevent SQL injection
        sql = text(self._queryDownloadSQL).bindparams(
            dcTitleId=self._dcTitleId,
            bitstreamId=bitstream_id
        )
        
        result = pd.read_sql(sql, self._conn)
        
        if len(result) != 1:
            logger.debug('Could not recover data for bitstream %s from db', bitstream_id)
            return None
            
        logger.debug('Successfully recovered data for bitstream %s from db', bitstream_id)
        record = result.iloc[0].to_dict()
        self._cache[cache_key] = record
        return record

    def queryItem(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Query information for an item.
        
        Args:
            item_id: The item identifier
            
        Returns:
            Dictionary with resource info or None if not found
        """
        cache_key = f"item_{item_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use parameterized query to prevent SQL injection
        sql = text(self._queryItemSQL).bindparams(
            dcTitleId=self._dcTitleId,
            itemId=item_id
        )
        
        result = pd.read_sql(sql, self._conn)
        
        if len(result) != 1:
            logger.debug('Could not recover data for item %s from db', item_id)
            return None
            
        logger.debug('Successfully recovered data for item %s from db', item_id)
        record = result.iloc[0].to_dict()
        self._cache[cache_key] = record
        return record

    def close(self) -> None:
        """Close the database connection."""
        logger.debug("Closing dspace db connection")
        self._conn.close()
        self._engine.dispose()


