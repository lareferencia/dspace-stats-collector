#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector
MINICONDA_URL_PREFIX='https://repo.anaconda.com/miniconda/'

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} == 'x86_64' ]; then
  # 64-bit stuff here
  MINICONDA_FILE='Miniconda3-latest-Linux-x86_64.sh'
else
  # 32-bit stuff here
  MINICONDA_FILE='Miniconda3-latest-Linux-x86.sh'
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



