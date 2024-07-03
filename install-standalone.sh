#!/bin/bash
#
export PIP_DEFAULT_TIMEOUT=100
INSTALL_PATH=$HOME/dspace-stats-collector
MINICONDA_URL_PREFIX='https://repo.anaconda.com/miniconda/'

rm -rf $INSTALL_PATH
rm -f delete_this_file.sh

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} == 'x86_64' ]; then
  # 64-bit stuff here
  MINICONDA_FILE='Miniconda3-py37_4.8.3-Linux-x86_64.sh'
else
  # 32-bit stuff here
  MINICONDA_FILE='Miniconda3-py37_4.8.3-Linux-x86.sh'
fi

MINICONDA_URL=$MINICONDA_URL_PREFIX$MINICONDA_FILE

if [ -x "$(which curl)" ]; then
  curl $MINICONDA_URL -o delete_this_file.sh 
else
    echo "Could not find curl, please install curl." >&2
    exit
fi

bash delete_this_file.sh -b -f -p $INSTALL_PATH
rm delete_this_file.sh

cd $INSTALL_PATH

echo "Installing dspace-stats-collector package dependencies"
curl https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/requirements-p37.txt -o requirements.txt
$INSTALL_PATH/bin/pip install -r requirements.txt

echo "Installing dspace-stats-collector package"
$INSTALL_PATH/bin/pip install --no-cache-dir dspace-stats-collector

echo "Installing config files"
$INSTALL_PATH/bin/dspace-stats-configure


