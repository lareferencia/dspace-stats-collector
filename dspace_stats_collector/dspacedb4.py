#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" DSpace 4 DB components """

import logging
logger = logging.getLogger(__name__)

try:
    from .dspacedb import DSpaceDB
except ImportError:
    from dspacedb import DSpaceDB


class DSpaceDB4(DSpaceDB):
    """Database connector for DSpace 4.x (PostgreSQL)."""

    def __init__(self, jdbc_url: str, username: str, password: str) -> None:
        # Define SQL templates before calling parent __init__
        # Use :param syntax for SQLAlchemy text().bindparams()
        # NOTE: The download query appears to have a hardcoded bitstream_id=3
        # which may be a bug in the original implementation
        self._queryDownloadSQL = """
            SELECT C.bitstream_id as id, record_title, handle, is_download, owning_item, sequence_id, filename FROM
            (SELECT mv.item_id AS id,
            mv.text_value AS record_title,
            h.handle AS handle,
            true AS is_download,
            'owning_item' AS owning_item
            FROM metadatavalue AS mv
            RIGHT JOIN handle AS h ON mv.item_id = h.resource_id
            WHERE mv.metadata_field_id = 64 AND h.resource_type_id = 2) AS A
            JOIN
            (SELECT b.sequence_id,
            b.name AS filename,
            b.bitstream_id,
            i.item_id AS item_id
            FROM bitstream AS b,
            bundle2bitstream AS bb,
            item2bundle AS i
            WHERE bb.bitstream_id = b.bitstream_id
            AND i.bundle_id = bb.bundle_id
            AND b.bitstream_id = :bitstreamId) AS C
            ON A.id = C.item_id
        """
        
        self._queryItemSQL = """
            SELECT mv.item_id AS id,
                    mv.text_value AS record_title,
                    h.handle AS handle,
                    false AS is_download,
                    NULL AS owning_item,
                    NULL AS sequence_id,
                    NULL AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN handle AS h ON h.resource_id = mv.item_id
            WHERE metadata_field_id = :dcTitleId
                AND h.resource_type_id = 2
                AND mv.item_id = :itemId
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