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




