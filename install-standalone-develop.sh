#!/bin/bash
#

INSTALL_PATH=$HOME/dspace-stats-collector
MINICONDA_URL_PREFIX='https://repo.anaconda.com/miniconda/'

rm -rf $INSTALL_PATH
rm -f delete_this_file.sh

MACHINE_TYPE=`uname -m`
if [ ${MACHINE_TYPE} == 'x86_64' ]; then
  # 64-bit stuff here
  MINICONDA_FILE='Miniconda3-py37_4.8.3-Linux-x86_64.sh'
elif [ ${MACHINE_TYPE} == 'x86' ]; then
  # 32-bit stuff here
  MINICONDA_FILE='Miniconda3-py37_4.8.3-Linux-x86.sh'
elif [ ${MACHINE_TYPE} == 'aarch64' ]; then
  # ARM stuff here (EXPERIMENTAL)
  MINICONDA_FILE='Miniconda3-py37_4.9.2-Linux-aarch64.sh'
else
  echo "Unknown machine type: ${MACHINE_TYPE}"
  exit 1
fi

MINICONDA_URL=$MINICONDA_URL_PREFIX$MINICONDA_FILE

echo $MINICONDA_URL

if [ -x "$(which curl)" ]; then
  curl $MINICONDA_URL -o delete_this_file.sh 
else
    echo "Could not find curl, please install curl." >&2
    exit 1
fi

bash delete_this_file.sh -b -f -p $INSTALL_PATH
rm delete_this_file.sh

cd $INSTALL_PATH

echo "Installing dspace-stats-collector package dependencies"
curl https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/requirements-p37.txt -o $INSTALL_PATH/requirements.txt
$INSTALL_PATH/bin/pip install -r $INSTALL_PATH/requirements.txt

$INSTALL_PATH/bin/conda install -y git 

$INSTALL_PATH/bin/git clone --brance=develop https://github.com/lareferencia/dspace-stats-collector.git

cd $INSTALL_PATH/dspace-stats-collector
$INSTALL_PATH/bin/python setup.py install



