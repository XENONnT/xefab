#!/bin/bash

set -e

NVFLAG=""

echo "Sim_NV: {sim_nv}"
if [ "{sim_nv}" = "1" ]; then
    echo "Simulating neutron veto!"
    NVFLAG="--NeutronVeto"
fi
echo "NVFLAG: ${{NVFLAG}}"

echo "python merge_wfsim.py --output merged_data \
                      --input data \
                      --batch {batch_number} \
                      --EpixDetectorOverride {epix_detectorconfig} \
                      --EpixMicroSeparation {epix_microseparation} \
                      --EpixTagClusterBy {epix_tagclusterby} \
                      --EpixNROnly {epix_nronly} \
                      $NVFLAG"

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
                      --batch {batch_number} \
                      --EpixDetectorOverride {epix_detectorconfig} \
                      --EpixMicroSeparation {epix_microseparation} \
                      --EpixTagClusterBy {epix_tagclusterby} \
                      --EpixNROnly {epix_nronly} \
                      $NVFLAG

# remove the dummy files we made for run metata
rm merged_data/*json

# tar up the merged output
tar cvjf {output_tarball} merged_data

echo "DONE"
