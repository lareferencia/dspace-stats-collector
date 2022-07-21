#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector

cd $INSTALL_PATH

echo "Installing dspace-stats-collector package dependencies"
curl https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/requirements-p37.txt -o $INSTALL_PATH/requirements.txt
$INSTALL_PATH/bin/pip install -r $INSTALL_PATH/requirements.txt

cd $INSTALL_PATH/dspace-stats-collector

$INSTALL_PATH/bin/git pull
$INSTALL_PATH/bin/python setup.py install




