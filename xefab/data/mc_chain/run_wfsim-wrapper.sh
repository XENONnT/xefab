#!/usr/bin/env bash

# initialize arguments
INPUT_TARBALL=$1
EXPERIMENT=$2
SIM_NV=$3
ENTRY_START=$4
ENTRY_STOP=$5
EVENT_RATE=$6
CHUNK_SIZE=$7
EPIX_MICROSEPARATION=$8
EPIX_TAGCLUSTERBY=${9}
EPIX_NRONLY=${10}
SAVE_RAW_RECORDS=${11}
MCVERSION=${12}
LOCAL_TEST=${13}
EPIX_DETECTORCONFIG=${14}

. /opt/XENONnT/setup.sh
export RUCIO_ACCOUNT=xenon-mc
export XENON_CONFIG=$PWD/.xenon_config

if [ "${LOCAL_TEST}" = "0" ]; then
    echo "--- Installing cutax ---"
    mkdir cutax
    tar -xzf cutax.tar.gz -C cutax --strip-components=1
    pip install ./cutax --user --no-deps -qq
fi
python -c "import cutax; print(cutax.__file__)"

# Set pipe to propagate error codes to $?
set -o pipefail
set -e

NVFLAG=""

echo "Sim_NV: ${SIM_NV}"
if [ "${SIM_NV}" = "1" ]; then
    echo "Simulating neutron veto!"
    NVFLAG="--NeutronVeto"
fi

RRFLAG=""
if [ "${SAVE_RAW_RECORDS}" = "1" ]; then
    RRFLAG="--SaveRawRecords"
fi

# Setup CVMFS directories
CVMFSDIR=/cvmfs/xenon.opensciencegrid.org
RELEASEDIR=${CVMFSDIR}/releases/mc/${MCVERSION}

# Load library settings generated during compilation
source ${RELEASEDIR}/setup.sh

# untar the input
tar xvjf $INPUT_TARBALL

# get the root file from what we just untarred
ROOTFILE=$(ls results/*root)

RUNID=${ROOTFILE%*.root}
RUNID=${RUNID#*/}
# replace any '-' instances with '_'
# some strax thing, I guess \shrug
RUNID=${RUNID//-/_}

OUTPUT='data'

time python run_wfsim.py --RunID ${RUNID} \
                         --G4File $ROOTFILE \
                         --Experiment $EXPERIMENT \
                         --EpixDetectorOverride $EPIX_DETECTORCONFIG \
                         --OutputFolder $OUTPUT \
                         --EntryStart $ENTRY_START \
                         --EntryStop $ENTRY_STOP \
                         --EventRate $EVENT_RATE \
                         --ChunkSize $CHUNK_SIZE \
                         --EpixMicroSeparation $EPIX_MICROSEPARATION \
                         --EpixTagClusterBy $EPIX_TAGCLUSTERBY \
                         --EpixNROnly $EPIX_NRONLY \
                         $RRFLAG \
                         $NVFLAG

tar cvjf "wf_${INPUT_TARBALL}" $OUTPUT

ls $OUTPUT

echo "Done!"

