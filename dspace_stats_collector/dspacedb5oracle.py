#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" DSpace 5 Oracle DB components """

import logging
logger = logging.getLogger(__name__)

try:
    from .dspacedb import DSpaceDB
except ImportError:
    from dspacedb import DSpaceDB


class DSpaceDB5Oracle(DSpaceDB):
    """Database connector for DSpace 5.x (Oracle)."""

    def __init__(self, jdbc_url: str, username: str, password: str) -> None:
        # Define SQL templates before calling parent __init__
        # Use :param syntax for SQLAlchemy text().bindparams()
        self._queryDownloadSQL = """
            SELECT mv.resource_id AS id,
                    mv2.text_value AS record_title,
                    h.handle AS handle,
                    1 AS is_download,
                    i.item_id AS owning_item,
                    b.sequence_id AS sequence_id,
                    mv.text_value AS filename
            FROM metadatavalue mv
            RIGHT JOIN bitstream b ON mv.resource_id = b.bitstream_id
            RIGHT JOIN bundle2bitstream bb ON b.bitstream_id = bb.bitstream_id
            RIGHT JOIN item2bundle i ON i.bundle_id = bb.bundle_id
            RIGHT JOIN handle h ON h.resource_id = i.item_id
            RIGHT JOIN metadatavalue mv2 ON mv2.resource_id = i.item_id
            WHERE mv.metadata_field_id = :dcTitleId
                AND mv.resource_type_id = 0
                AND b.sequence_id IS NOT NULL
                AND b.deleted = 0
                AND mv2.metadata_field_id = :dcTitleId
                AND mv2.resource_type_id = 2
                AND mv.resource_id = :bitstreamId
        """

        self._queryItemSQL = """
            SELECT mv.resource_id AS id,
                    mv.text_value AS record_title,
                    h.handle AS handle,
                    0 AS is_download,
                    NULL AS owning_item,
                    NULL AS sequence_id,
                    NULL AS filename
            FROM metadatavalue mv
            RIGHT JOIN handle h ON h.resource_id = mv.resource_id
            WHERE metadata_field_id = :dcTitleId
                AND mv.resource_type_id = 2
                AND h.resource_type_id = 2
                AND mv.resource_id = :itemId
        """

        self._queryTitleSQL = """
            SELECT metadata_field_id AS "dcTitleId"
            FROM metadatafieldregistry mfr,
                 metadataschemaregistry msr
            WHERE mfr.metadata_schema_id = msr.metadata_schema_id
              AND short_id = 'dc'
              AND element = 'title'
              AND qualifier IS NULL
        """

        # Call parent constructor
        super().__init__(jdbc_url, username, password)
        
        # Get DC Title ID after connection is established
        self._dcTitleId = self.getDcTitleId()

