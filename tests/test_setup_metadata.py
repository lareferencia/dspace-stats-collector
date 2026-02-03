#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression checks for setup.py packaging metadata."""

import ast
from pathlib import Path


def _find_assignment_value(module_ast, variable_name):
    for node in module_ast.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    return node.value
    return None


def _literal_list(node):
    if not isinstance(node, ast.List):
        return None
    values = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            values.append(elt.value)
    return values


def test_setup_uses_recursive_package_include_and_runtime_dependencies():
    setup_path = Path(__file__).resolve().parent.parent / "setup.py"
    module_ast = ast.parse(setup_path.read_text(encoding="utf-8"))

    setup_call = None
    for node in module_ast.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "setup":
                setup_call = call
                break

    assert setup_call is not None

    packages_kw = next((kw for kw in setup_call.keywords if kw.arg == "packages"), None)
    assert packages_kw is not None
    assert isinstance(packages_kw.value, ast.Call)
    assert isinstance(packages_kw.value.func, ast.Name)
    assert packages_kw.value.func.id == "find_packages"
    include_kw = next((kw for kw in packages_kw.value.keywords if kw.arg == "include"), None)
    include_values = _literal_list(include_kw.value)
    assert include_values == ["dspace_stats_collector*"]

    deps_kw = next((kw for kw in setup_call.keywords if kw.arg == "install_requires"), None)
    assert deps_kw is not None
    assert isinstance(deps_kw.value, ast.Name)

    requirements = _literal_list(_find_assignment_value(module_ast, deps_kw.value.id))
    assert requirements is not None
    assert "tenacity" in requirements
