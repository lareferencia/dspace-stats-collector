#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for collector script import fallbacks."""

import ast
from pathlib import Path


def test_collector_fallback_import_uses_matomo_offline_exception():
    collector_path = Path(__file__).resolve().parent.parent / "dspace_stats_collector" / "collector.py"
    module_ast = ast.parse(collector_path.read_text(encoding="utf-8"))

    found = False
    for node in module_ast.body:
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            for statement in handler.body:
                if isinstance(statement, ast.ImportFrom) and statement.module == "matomooutput":
                    names = {name.name for name in statement.names}
                    assert "MatomoOfflineException" in names
                    assert "MatomoBulkOutput" not in names
                    found = True

    assert found, "Fallback import from matomooutput was not found in collector.py"
