#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector

echo "Updating dspace-stats-collector version"

echo "Installing dspace-stats-collector package dependencies"
rm -f $INSTALL_PATH/requirements.txt

python_version=`$INSTALL_PATH/bin/python -V 2>&1 | sed 's/.* \([0-9]\).\([0-9]\).*/\1\2/'`
echo "Python version: $python_version"

requirements_file="requirements.txt"

echo "Downloading dspace-stats-collector python $python_version dependencies"
if [ $python_version == "37" ]; then
    requirements_file = "requirements-p37.txt"
else
    requirements_file = "requirements.txt"
fi

if [ -x "$(which curl)" ]; then
  curl  https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/$requirements_file -o $INSTALL_PATH/requirements.txt
else
    echo "Could not find curl, please install curl." >&2
    exit
fi

echo "Installing dspace-stats-collector package dependencies"
$INSTALL_PATH/bin/pip install -r $INSTALL_PATH/requirements.txt

echo "Removing dspace-stats-collector installed version"
$INSTALL_PATH/bin/pip uninstall --yes dspace-stats-collector

echo "Updating to newest dspace-stats-collector version"
$INSTALL_PATH/bin/pip install --no-cache-dir dspace-stats-collector

echo "dspace-stats-collector successfully updated"
