#!/usr/bin/env bash
# Arguments
# $1 - job id
# $2 - starting event
# $3 - events to simulate
# $4 - experiment
# $5 - mc_version
# $6 - mc_preinit_macro
# $7 - mc_preinit_belt
# $8 - mc_optical_setup
# $9 - mc_source_macro
# $10 - simulation_name


function terminate {

    # organize and tar all files here
    # do we need a deeper results dir?
    cd ${start_dir}
    mv output results
    tar cvjf ${start_dir}/{job_id}_output.tar.bz2 results
    
    rm -fr $work_dir

    exit $1
}

export XENON_CONFIG=.xenon_config

echo "Start time: " `/bin/date`
echo "Job is running on node: " `/bin/hostname`
echo "Job running as user: " `/usr/bin/id`
echo "Job is running in directory: $PWD"

# Used to label output
JOBID=$1
# Starting event
EVENT_START=$2
# Specify number of events
NEVENTS=$3
# Set Experiment
EXPERIMENT=$4
# Select MC version
MCVERSION=$5
PREINIT_MACRO=$6
PREINIT_BELT=$7
OPTICAL_SETUP=$8
SOURCE_MACRO=$9
SIMULATION_NAME=${10}

start_dir=$PWD

# Setup CVMFS directories
CVMFSDIR=/cvmfs/xenon.opensciencegrid.org
RELEASEDIR=${CVMFSDIR}/releases/mc/${MCVERSION}

# Setup Geant4 macros
MACROSDIR=${RELEASEDIR}/macros/${EXPERIMENT}


if [[ -f ${start_dir}/${PREINIT_MACRO} ]]; then
    PREINIT_MACRO=${start_dir}/${PREINIT_MACRO}
else
    PREINIT_MACRO=${MACROSDIR}/${PREINIT_MACRO}
fi

echo "Preinit macro: ${PREINIT_MACRO}"


if [[ -f ${start_dir}/${PREINIT_BELT} ]]; then
    PREINIT_BELT=${start_dir}/${PREINIT_BELT}
else
    PREINIT_BELT=${MACROSDIR}/${PREINIT_BELT}
fi

echo "Preinit belt: $PREINIT_BELT"


if [[ -f ${start_dir}/${OPTICAL_SETUP} ]]; then
    OPTICAL_SETUP=${start_dir}/${OPTICAL_SETUP}
else        
    OPTICAL_SETUP=${MACROSDIR}/${OPTICAL_SETUP}
fi

echo "Optical macro: $OPTICAL_SETUP"


if [[ -f ${start_dir}/${SOURCE_MACRO} ]]; then
    SOURCE_MACRO=${start_dir}/${SOURCE_MACRO}
else
    SOURCE_MACRO=${MACROSDIR}/${SOURCE_MACRO}
fi

echo "Source macro: $SOURCE_MACRO"

# Set HOME directory if it's not set
if [[ ${HOME} == "" ]];
then
    export HOME=$PWD
fi

# Set pipe to propagate error codes to $?
set -o pipefail

# Load library settings generated during compilation
source ${RELEASEDIR}/setup.sh
if [ $? -ne 0 ];
then
  exit 1
fi

# Setup directories
OUTDIR=$start_dir/output
mkdir -p  ${OUTDIR}
if [ $? -ne 0 ];
then
  exit 2
fi

if [ "$OSG_WN_TMP" == "" ];
then
    OSG_WN_TMP=$PWD
fi

work_dir=`mktemp -d --tmpdir=$OSG_WN_TMP`
cd $work_dir

# Filenaming
SUBRUN=`printf "%05d\n" $JOBID`
FILEROOT=${EXPERIMENT: -2}_mc_${SIMULATION_NAME}
FILENUM=${FILEROOT}_${SUBRUN}
G4_FILENAME=${OUTDIR}/${FILENUM}
EPIX_FILENAME=${G4_FILENAME}_wfsim_instructions
WFSIM_OUTDIR=${OUTDIR}/strax_data

# Geant4 stage
G4EXEC=${RELEASEDIR}/xenon1t_G4p10
SPECTRADIR=${RELEASEDIR}/macros
ln -sf ${SPECTRADIR} # For reading e.g. input spectra from CWD

# Print environment settings
#env | sort

# Run G4 simulation
(time ${G4EXEC} -p ${PREINIT_MACRO} -b ${PREINIT_BELT} -s ${OPTICAL_SETUP} -f ${SOURCE_MACRO} -n ${NEVENTS} \
                -d ${EXPERIMENT}  -e {starting_event} -o ${G4_FILENAME}.root;)

# check that the output exists
if [ -e ${G4_FILENAME}.root ]; then
  terminate 0

else
  terminate 1
fi
