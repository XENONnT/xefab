#!/bin/bash

#  $2: Config file of simulation

echo "Using these arguments"
echo $@

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

python -c "import cutax; print(cutax.__file__)"

# need to add this back in for some reason
export PATH=/opt/geant4/bin:$PATH

export XENON_CONFIG=.xenon_config
export RUCIO_ACCOUNT=xenon-mc

rucio -v whoami

# python upload.py --config $1 --path results --rse $2 --id $3
python upload.py --config $2 
