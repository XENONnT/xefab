#!/bin/bash

set -e

my_log()
{
    TS=`/bin/date +'%F %H:%M:%S'`
    echo "$TS: $1"  1>&2
}

mkdir results

# run_id and target file is the first arguments
RUN_ID=$1
shift
TARGET=$1
shift

my_log "Size of inputs:"
ls -l

# everything else is an input 
for FILE in "$@"; do
    if (echo $FILE | grep tar.bz2) >/dev/null 2>&1; then
        my_log "Untaring $FILE ..."
        tar xjf $FILE
    else
        echo "Unknown input - expected a tarball: $FILE" 1>&2
        exit 1
    fi
done

COUNT_FILES=$(find results -type f | wc -l)
COUNT_DIRS=$(find results -type d | wc -l)
SIZE=$(du -s --si results | cut -f1)
my_log "Results directory has $COUNT_FILES files in $COUNT_DIRS directories. Total size: $SIZE"

my_log "Starting taring of $TARGET ..."

tar cjf $TARGET results

my_log "All done"

