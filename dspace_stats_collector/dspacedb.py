#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace DB components """

import logging
logger = logging.getLogger()

import sqlalchemy
import re
import pandas as pd


class DSpaceDB:

    def __init__(self, jdbcUrl, username, password):
        
        # Parse jdbc url
        # Postgres template: jdbc:postgresql://localhost:5432/dspace
        # Oracle template: jdbc:oracle:thin:@//localhost:1521/xe
        # Oracle template: jdbc:oracle:thin:@localhost:1521:xe
        m = re.match("^jdbc:(postgresql|oracle):[^\/|^@]*[@\/\/|\/\/|@]*([^:]+):(\d+)(\/|:)(.*)$", jdbcUrl)

        if m is None:
            logger.error("Could not parse db.url string: %s" % jdbcUrl)
            raise ValueError

        # separate host, port, dbname, and dbschema and separator 
        (engine, hostname, port, separator, database) = m.group(1, 2, 3, 4, 5)

        # Create connection string depending on engine
        if engine == 'postgresql':
            connStringTemplate = 'postgresql://{username}:{password}@{hostname}:{port}' + separator + '{database}'
        if engine == 'oracle':
            if separator == ':':
                connStringTemplate = 'oracle+cx_oracle://{username}:{password}@{hostname}:{port}/?service_name={database}'
            elif separator == '/':
                connStringTemplate = 'oracle+cx_oracle://{username}:{password}@{hostname}:{port}/{database}'

       
        # Create connection string based on engine, hostname, port, database. Use separator to determine the kind of oracle connection
        self.connString = connStringTemplate.format(
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


    def getDcTitleId(self):
        
        dfRecord = pd.read_sql(self._queryTitleSQL, self.conn)
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

