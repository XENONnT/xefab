#!/bin/bash

. /cvmfs/xenon.opensciencegrid.org/releases/nT/development/setup.sh

# now use the system Pegasus install in /usr
export PATH=/home/rynge/software/pegasus-5.0/bin:$PATH
export PYTHONPATH=`pegasus-config --python`

# copy the xenon_service proxy and set permissions
cp /xenon/grid_proxy/xenon_service_proxy ~/xenon_proxy
chmod 600 ~/xenon_proxy

# use the same xenon config
export XENON_CONFIG=/xenon/xenonnt/config/mc_config

export X509_USER_PROXY=~/xenon_proxy
export RUCIO_ACCOUNT=xenon-mc

