#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace DB components """

import logging
logger = logging.getLogger()

try:
    from .dspacedb import DSpaceDB
except Exception: #ImportError
    from dspacedb import DSpaceDB

class DSpaceDB5Cris(DSpaceDB):

    def __init__(self, jdbcUrl, username, password):

        DSpaceDB.__init__(self,jdbcUrl, username, password)
       
        self._queryDownloadSQL = """
            SELECT mv.resource_id AS id,
                    mv2.text_value AS record_title,
                    h.handle AS handle,
                    true AS is_download,
                    i.item_id AS owning_item,
                    b.sequence_id AS sequence_id,
                    mv.text_value AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN bitstream AS b ON mv.resource_id = b.bitstream_id
            RIGHT JOIN bundle2bitstream AS bb ON b.bitstream_id = bb.bitstream_id
            RIGHT JOIN item2bundle AS i ON i.bundle_id = bb.bundle_id
            RIGHT JOIN handle AS h ON h.resource_id = i.item_id
            RIGHT JOIN metadatavalue AS mv2 ON mv2.resource_id = i.item_id
            WHERE mv.metadata_field_id = {dcTitleId}
                AND mv.resource_type_id = 0
                AND b.sequence_id IS NOT NULL
                AND b.deleted = FALSE
                AND mv2.metadata_field_id = {dcTitleId}
                AND mv2.resource_type_id=2
                AND mv.resource_id = {bitstreamId};
        """

        self._queryItemSQL = """
            SELECT mv.resource_id AS id,
                    mv.text_value AS record_title,
                    h.handle AS handle,
                    false AS is_download,
                    NULL AS owning_item,
                    NULL AS sequence_id,
                    NULL AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN handle AS h ON h.resource_id = mv.resource_id
            WHERE metadata_field_id = {dcTitleId}
                AND mv.resource_type_id=2
                AND h.resource_type_id=2
                AND mv.resource_id = {itemId};
        """

        self._queryTitleSQL = """
        SELECT metadata_field_id AS "dcTitleId"
             FROM metadatafieldregistry mfr,
                  metadataschemaregistry msr
             WHERE mfr.metadata_schema_id = msr.metadata_schema_id
               AND short_id = 'dc'
               AND element = 'title'
               AND qualifier IS NULL;
        """

        self._dcTitleId = self.getDcTitleId()

        
        
