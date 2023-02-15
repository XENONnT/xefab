#!/bin/bash

# 1: batch number
# 2: output tarball
# 3: simulate neutron veto
# 4: epix config micro seperation
# 5: epix config tag cluster by
# 6: epix nr_only
# 7: epix detector config override

BATCH_NUMBER=$1
OUTPUT_TARBALL=$2
SIM_NV=$3
EPIX_MICROSEPARATION=$4
EPIX_TAGCLUSTERBY=${5}
EPIX_NRONLY=${6}
EPIX_DETECTORCONFIG=${7}

set -e

NVFLAG=""

echo "Sim_NV: ${SIM_NV}"
if [ "${SIM_NV}" = "1" ]; then
    echo "Simulating neutron veto!"
    NVFLAG="--NeutronVeto"
fi
echo "NVFLAG: ${NVFLAG}"

echo "python merge_wfsim.py --output merged_data \
                      --input data \
                      --batch ($BATCH_NUMBER) \
                      --EpixDetectorOverride ($EPIX_DETECTORCONFIG) \
                      --EpixMicroSeparation ($EPIX_MICROSEPARATION) \
                      --EpixTagClusterBy ($EPIX_TAGCLUSTERBY) \
                      --EpixNROnly ($EPIX_NRONLY) \
                      ($NVFLAG)"

echo "Here's what is in the output directory ($PWD)"
ls -la
echo "-----------------------------------"

echo "Untarring the output archives"
# untar the input
for TAR in `ls *wf*tar.bz2`; do
    tar xvf $TAR
done

echo "--- Installing cutax ---"
mkdir cutax
tar -xzf cutax.tar.gz -C cutax --strip-components=1
pip install ./cutax --user --no-deps -qq

# need to add this back in for some reason
export PATH=/opt/geant4/bin:$PATH

export XENON_CONFIG=.xenon_config
export RUCIO_ACCOUNT=xenon-mc

python merge_wfsim.py --output merged_data \
                      --input data \
                      --batch $BATCH_NUMBER \
                      --EpixDetectorOverride $EPIX_DETECTORCONFIG \
                      --EpixMicroSeparation $EPIX_MICROSEPARATION \
                      --EpixTagClusterBy $EPIX_TAGCLUSTERBY \
                      --EpixNROnly $EPIX_NRONLY \
                      $NVFLAG

# remove the dummy files we made for run metata
rm merged_data/*json

# tar up the merged output
tar cvjf $OUTPUT_TARBALL merged_data

echo "DONE"
