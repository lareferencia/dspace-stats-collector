#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector

echo "Updating dspace-stats-collector version"

echo "Removing dspace-stats-collector installed version"
$INSTALL_PATH/bin/pip uninstall --yes dspace-stats-collector

echo "Updating to newest dspace-stats-collector version"
$INSTALL_PATH/bin/pip install --no-cache-dir dspace-stats-collector

echo "dspace-stats-collector successfully updated"
