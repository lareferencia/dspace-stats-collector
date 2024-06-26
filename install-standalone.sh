#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector
MINICONDA_URL_PREFIX='https://repo.anaconda.com/miniconda/'

Miniconda3-py39_24.4.0-0-Linux-x86_64.sh

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} == 'x86_64' ]; then
  # 64-bit stuff here
  MINICONDA_FILE='Miniconda3-py39_24.4.0-0-Linux-x86_64.sh'
elif [ ${MACHINE_TYPE} == 'x86' ]; then
  # 32-bit stuff here
  MINICONDA_FILE='Miniconda3-py39_24.4.0-0-Linux-x86.sh'
elif [ ${MACHINE_TYPE} == 'aarch64' ]; then
  # ARM stuff here (EXPERIMENTAL)
  MINICONDA_FILE='Miniconda3-py39_24.4.0-0-Linux-aarch64.sh'
else
  echo "Unknown machine type: ${MACHINE_TYPE}"
  exit 1
fi


MINICONDA_URL=$MINICONDA_URL_PREFIX$MINICONDA_FILE

if [[ `wget -S --spider $MINICONDA_URL 2>&1 | grep 'HTTP/1.1 200 OK'` ]]; then 
  echo 'Downloading Miniconda ..'
else
  echo 'File cannot be downloaded / check if wget is installed and internet connection is available'
  exit 
fi

wget $MINICONDA_URL

bash $MINICONDA_FILE -b -f -p $INSTALL_PATH

cd $INSTALL_PATH

echo "Installing dspace-stats-collector package dependencies"
wget https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/requirements.txt
$INSTALL_PATH/bin/pip install -r requirements.txt

echo "Installing dspace-stats-collector package"
$INSTALL_PATH/bin/pip install--no-cache-dir dspace-stats-collector

echo "Installing config files"
$INSTALL_PATH/bin/dspace-stats-configure



