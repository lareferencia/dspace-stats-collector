#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQL Query Templates for different DSpace versions.

This module centralizes all SQL queries to eliminate duplication
across the dspacedb*.py files.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DSpaceQueries:
    """SQL query templates for a specific DSpace version."""
    download: str
    item: str
    title: str


# =============================================================================
# PostgreSQL Queries
# =============================================================================

QUERIES_V4 = DSpaceQueries(
    download="""
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
    """,
    item="""
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
    """,
    title="""
        SELECT metadata_field_id AS "dcTitleId"
        FROM metadatafieldregistry mfr,
             metadataschemaregistry msr
        WHERE mfr.metadata_schema_id = msr.metadata_schema_id
          AND short_id = 'dc'
          AND element = 'title'
          AND qualifier IS NULL
    """
)

QUERIES_V5 = DSpaceQueries(
    download="""
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
        WHERE mv.metadata_field_id = :dcTitleId
            AND mv.resource_type_id = 0
            AND b.sequence_id IS NOT NULL
            AND b.deleted = FALSE
            AND mv2.metadata_field_id = :dcTitleId
            AND mv2.resource_type_id = 2
            AND mv.resource_id = :bitstreamId
    """,
    item="""
        SELECT mv.resource_id AS id,
                mv.text_value AS record_title,
                h.handle AS handle,
                false AS is_download,
                NULL AS owning_item,
                NULL AS sequence_id,
                NULL AS filename
        FROM metadatavalue AS mv
        RIGHT JOIN handle AS h ON h.resource_id = mv.resource_id
        WHERE metadata_field_id = :dcTitleId
            AND mv.resource_type_id = 2
            AND h.resource_type_id = 2
            AND mv.resource_id = :itemId
    """,
    title="""
        SELECT metadata_field_id AS "dcTitleId"
        FROM metadatafieldregistry mfr,
             metadataschemaregistry msr
        WHERE mfr.metadata_schema_id = msr.metadata_schema_id
          AND short_id = 'dc'
          AND element = 'title'
          AND qualifier IS NULL
    """
)

# V5 CRIS uses same queries as V5
QUERIES_V5_CRIS = QUERIES_V5

QUERIES_V6 = DSpaceQueries(
    download="""
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
        WHERE mv.metadata_field_id = :dcTitleId
            AND b.sequence_id IS NOT NULL
            AND b.deleted = FALSE
            AND mv2.metadata_field_id = :dcTitleId
            AND mv.dspace_object_id = uuid(:bitstreamId)
    """,
    item="""
        SELECT mv.dspace_object_id::text AS id,
                mv.text_value AS record_title,
                h.handle AS handle,
                false AS is_download,
                NULL AS owning_item,
                NULL AS sequence_id,
                NULL AS filename
        FROM metadatavalue AS mv
        RIGHT JOIN handle AS h ON h.resource_id = mv.dspace_object_id
        WHERE metadata_field_id = :dcTitleId
            AND h.resource_type_id = 2
            AND mv.dspace_object_id = uuid(:itemId)
    """,
    title="""
        SELECT metadata_field_id AS "dcTitleId"
        FROM metadatafieldregistry mfr,
             metadataschemaregistry msr
        WHERE mfr.metadata_schema_id = msr.metadata_schema_id
          AND short_id = 'dc'
          AND element = 'title'
          AND qualifier IS NULL
    """
)

# V7 uses same queries as V6
QUERIES_V7 = QUERIES_V6


# =============================================================================
# Oracle Queries
# =============================================================================

QUERIES_V5_ORACLE = DSpaceQueries(
    download="""
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
    """,
    item="""
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
    """,
    title="""
        SELECT metadata_field_id AS "dcTitleId"
        FROM metadatafieldregistry mfr,
             metadataschemaregistry msr
        WHERE mfr.metadata_schema_id = msr.metadata_schema_id
          AND short_id = 'dc'
          AND element = 'title'
          AND qualifier IS NULL
    """
)

QUERIES_V6_ORACLE = DSpaceQueries(
    download="""
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
        WHERE mv.metadata_field_id = :dcTitleId
            AND b.sequence_id IS NOT NULL
            AND b.deleted = 0
            AND mv2.metadata_field_id = :dcTitleId
            AND mv.dspace_object_id = upper(replace(:bitstreamId, '-', ''))
    """,
    item="""
        SELECT regexp_replace(lower(mv.dspace_object_id), '(........)(....)(....)(....)(.*)', '\\1-\\2-\\3-\\4-\\5') AS id,            
                mv.text_value AS record_title,
                h.handle AS handle,
                0 AS is_download,
                NULL AS owning_item,
                NULL AS sequence_id,
                NULL AS filename
        FROM metadatavalue mv
        INNER JOIN handle h ON h.resource_id = mv.dspace_object_id
        WHERE metadata_field_id = :dcTitleId
            AND h.resource_type_id = 2
            AND mv.dspace_object_id = upper(replace(:itemId, '-', ''))
    """,
    title="""
        SELECT metadata_field_id AS "dcTitleId"
        FROM metadatafieldregistry mfr,
             metadataschemaregistry msr
        WHERE mfr.metadata_schema_id = msr.metadata_schema_id
          AND short_id = 'dc'
          AND element = 'title'
          AND qualifier IS NULL
    """
)


# =============================================================================
# Query Registry
# =============================================================================

QUERY_REGISTRY = {
    '4': QUERIES_V4,
    '5': QUERIES_V5,
    '5c': QUERIES_V5_CRIS,  # DSpace 5 CRIS
    '5o': QUERIES_V5_ORACLE,  # DSpace 5 Oracle
    '6': QUERIES_V6,
    '6o': QUERIES_V6_ORACLE,  # DSpace 6 Oracle
    '7': QUERIES_V7,
}


def get_queries(version: str) -> DSpaceQueries:
    """
    Get SQL queries for a specific DSpace version.
    
    Args:
        version: DSpace version string ('4', '5', '5c', '5o', '6', '6o', '7')
        
    Returns:
        DSpaceQueries dataclass with download, item, and title queries
        
    Raises:
        KeyError: If version is not supported
    """
    if version not in QUERY_REGISTRY:
        raise KeyError(
            f"Unsupported DSpace version: {version}. "
            f"Supported versions: {list(QUERY_REGISTRY.keys())}"
        )
    return QUERY_REGISTRY[version]
