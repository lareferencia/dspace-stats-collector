#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace DB components """

import logging
logger = logging.getLogger()

import sqlalchemy
import re
import pandas as pd


class DSpaceDB:

    def __init__(self, jdbcUrl, username, password, schema, dSpaceMajorVersion):
        self.schema = schema

        # Parse jdbc url
        # Postgres template: jdbc:postgresql://localhost:5432/dspace
        # Oracle template: jdbc:oracle:thin:@//localhost:1521/xe
        m = re.match("^jdbc:(postgresql|oracle):[^\/]*\/\/([^:]+):(\d+)/(.*)$", jdbcUrl)
        if m is None:
            logger.error("Could not parse db.url string: %s" % jdbcUrl)
            raise ValueError

        (engine, hostname, port, database) = m.group(1, 2, 3, 4)

        if engine != "postgresql":
            logger.error("DB Engine not yet supported: %s" % engine)
            raise NotImplementedError

        self.connString = '{engine}://{username}:{password}@{hostname}:{port}/{database}'
        self.connString = self.connString.format(
                engine=engine,
                username=username,
                password=password,
                hostname=hostname,
                port=port,
                database=database,
                )
        logger.debug('DB Connection String: ' + self.connString)
        try:
            self.conn = sqlalchemy.create_engine(self.connString).connect()
            logger.debug('DB Connection established successfully.')
        except sqlalchemy.exc.OperationalError:
            logger.exception("Could not connect to DB.")
            raise

        self._dfResources = pd.DataFrame(columns=['id', 'record_title', 'handle', 'is_download', 'owning_item', 'sequence_id', 'filename']).set_index('id')

        if dSpaceMajorVersion == '5':
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
        elif dSpaceMajorVersion == '4':
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
            AND b.bitstream_id = 3) AS C
            ON A.id = C.item_id;
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
                WHERE metadata_field_id = {dcTitleId}
                  AND h.resource_type_id=2
                  AND mv.item_id = {itemId};
            """
        elif dSpaceMajorVersion == '6':
            self._queryDownloadSQL = """
            SELECT mv.dspace_object_id::text AS id,
                   mv2.text_value AS record_title,
                   h.handle AS handle,
                   true AS is_download,
                   i.item_id::text AS owning_item,
                   b.sequence_id AS sequence_id,
                   mv.text_value AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN bitstream AS b ON mv.dspace_object_id = b.uuid
            RIGHT JOIN bundle2bitstream AS bb ON b.uuid = bb.bitstream_id
            RIGHT JOIN item2bundle AS i ON i.bundle_id = bb.bundle_id
            RIGHT JOIN handle AS h ON h.resource_id = i.item_id
            RIGHT JOIN metadatavalue AS mv2 ON mv2.dspace_object_id = i.item_id
            WHERE mv.metadata_field_id = {dcTitleId}
              AND b.sequence_id IS NOT NULL
              AND b.deleted = FALSE
              AND mv2.metadata_field_id = {dcTitleId}
              AND mv.dspace_object_id::text = '{bitstreamId}';
            """
            self._queryItemSQL = """
                SELECT mv.dspace_object_id::text AS id,
                       mv.text_value AS record_title,
                       h.handle AS handle,
                       false AS is_download,
                       NULL AS owning_item,
                       NULL AS sequence_id,
                       NULL AS filename
                FROM metadatavalue AS mv
                RIGHT JOIN handle AS h ON h.resource_id = mv.dspace_object_id
                WHERE metadata_field_id = {dcTitleId}
                  AND h.resource_type_id=2
                  AND mv.dspace_object_id::text = '{itemId}';
            """
        else:
            logger.error('Only implemented values for dspace.majorVersion are 4, 5 and 6. Received {}'.format(dSpaceMajorVersion))
            raise NotImplementedError

        self._dcTitleId = self.getDcTitleId()


    def getDcTitleId(self):
        resource_id_field = 'resource_id'
        SQL = """
        SELECT metadata_field_id AS "dcTitleId"
             FROM metadatafieldregistry mfr,
                  metadataschemaregistry msr
             WHERE mfr.metadata_schema_id = msr.metadata_schema_id
               AND short_id = 'dc'
               AND element = 'title'
               AND qualifier IS NULL;
        """
        dfRecord = pd.read_sql(SQL, self.conn)
        if len(dfRecord) != 1:
            logger.error('Could not recover DC Title metadata field id from db')
            raise RuntimeError
        dcTitleId = dfRecord.dcTitleId[0]
        return dcTitleId


    def queryDownload(self, bitstreamId): #, owningItem):
        if bitstreamId not in self._dfResources.index.values:
            SQL = self._queryDownloadSQL.format(
                    dcTitleId = self._dcTitleId,
                    bitstreamId = bitstreamId
            )
            dfRecord = pd.read_sql(SQL, self.conn).set_index('id')
            if len(dfRecord) != 1:
                logger.debug('Could not recover data for bitstream {} from db'.format(bitstreamId))
                return None
#            if dfRecord.loc[bitstreamId, 'owning_item'] != owningItem and not(type(owningItem) == list and dfRecord.loc[bitstreamId, 'owning_item'] == owningItem[0]): # DSpace 6 logs owningItem as a 1-element array in SOLR
#                logger.debug('Owning Item mismatch for bitstream {} from db ({}, {})'.format(bitstreamId, dfRecord.loc[bitstreamId, 'owning_item'], owningItem[0]))
#                return None
            logger.debug('Successfully recovered data for bitstream {} from db'.format(bitstreamId))
            self._dfResources = self._dfResources.append(dfRecord)

        return self._dfResources.loc[bitstreamId].to_dict()

    def queryItem(self, itemId):
        if itemId not in self._dfResources.index.values:
            SQL = self._queryItemSQL.format(
                    dcTitleId = self._dcTitleId,
                    itemId = itemId
            )
            dfRecord = pd.read_sql(SQL, self.conn).set_index('id')
            if len(dfRecord) != 1:
                logger.debug('Could not recover data for item {} from db'.format(itemId))
                return None
            logger.debug('Successfully recovered data for item {} from db'.format(itemId))
            self._dfResources = self._dfResources.append(dfRecord)
        return self._dfResources.loc[itemId].to_dict()

    def close(self):
        logger.debug("Closing dspace db connection")
        self.conn.close()

