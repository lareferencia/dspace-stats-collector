#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector

echo "Updating dspace-stats-collector version"

echo "Installing dspace-stats-collector package dependencies"
rm -f $INSTALL_PATH/requirements.txt

if [ -x "$(which curl)" ]; then
  curl  https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/requirements.txt -o $INSTALL_PATH/requirements.txt
else
    echo "Could not find curl, please install curl." >&2
    exit
fi

$INSTALL_PATH/bin/pip install -r $INSTALL_PATH/requirements.txt

echo "Removing dspace-stats-collector installed version"
$INSTALL_PATH/bin/pip uninstall --yes dspace-stats-collector

echo "Updating to newest dspace-stats-collector version"
$INSTALL_PATH/bin/pip install --no-cache-dir dspace-stats-collector

echo "dspace-stats-collector successfully updated"
