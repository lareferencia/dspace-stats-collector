#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace DB components """

import logging
logger = logging.getLogger()

try:
    from .dspacedb import DSpaceDB
except Exception: #ImportError
    from dspacedb import DSpaceDB

class DSpaceDB6Oracle(DSpaceDB):

    def __init__(self, jdbcUrl, username, password):

        DSpaceDB.__init__(self,jdbcUrl, username, password)

        self._queryDownloadSQL = """
            SELECT regexp_replace(lower(mv.dspace_object_id), '(........)(....)(....)(....)(.*)', '\\1-\\2-\\3-\\4-\\5') AS id,            
                    mv2.text_value AS record_title,
                    h.handle AS handle,
                    1 AS is_download,
                    regexp_replace(lower(i.item_id), '(........)(....)(....)(....)(.*)', '\\1-\\2-\\3-\\4-\\5') AS owning_item,                    
                    b.sequence_id AS sequence_id,
                    mv.text_value AS filename
            FROM metadatavalue mv
            INNER JOIN bitstream b ON mv.dspace_object_id = b.uuid
            INNER JOIN bundle2bitstream bb ON b.uuid = bb.bitstream_id
            INNER JOIN item2bundle i ON i.bundle_id = bb.bundle_id
            INNER JOIN handle h ON h.resource_id = i.item_id
            INNER JOIN metadatavalue mv2 ON mv2.dspace_object_id = i.item_id
            WHERE mv.metadata_field_id = {dcTitleId}
                AND b.sequence_id IS NOT NULL
                AND b.deleted = 0
                AND mv2.metadata_field_id = {dcTitleId}
                AND mv.dspace_object_id = upper(replace('{bitstreamId}','-',''))
        """

        self._queryItemSQL = """
            SELECT regexp_replace(lower(mv.dspace_object_id), '(........)(....)(....)(....)(.*)', '\\1-\\2-\\3-\\4-\\5') AS id,            
                    mv.text_value AS record_title,
                    h.handle AS handle,
                    0 AS is_download,
                    NULL AS owning_item,
                    NULL AS sequence_id,
                    NULL AS filename
            FROM metadatavalue mv
            INNER JOIN handle h ON h.resource_id = mv.dspace_object_id
            WHERE metadata_field_id = {dcTitleId}
                AND h.resource_type_id=2
                AND mv.dspace_object_id = upper(replace('{itemId}','-',''))
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

        self._dcTitleId = self.getDcTitleId()
    