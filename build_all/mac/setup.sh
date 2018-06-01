#!/bin/bash
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

# This script updates a fresh Ubuntu installation with all the dependent
# components necessary to use the IoT Client SDK for C and Python.

build_root=$(cd "$(dirname "$0")/../.." && pwd)
cd $build_root

PYTHON_VERSION=2.7

process_args()
{
    save_next_arg=0
    
    for arg in $*
    do
      if [ $save_next_arg == 1 ]
      then
        PYTHON_VERSION="$arg"
        if [ $PYTHON_VERSION != "2.7" ] && [ $PYTHON_VERSION != "3.4" ] && [ $PYTHON_VERSION != "3.5" ] && [ $PYTHON_VERSION != "3.6" ]
        then
          echo "Supported python versions are 2.7, 3.4 or 3.5"
          exit 1
        fi 
        save_next_arg=0
      else
        case "$arg" in
          "--python-version" ) save_next_arg=1;;
          * ) ;;
        esac
      fi
    done
}

process_args $*

scriptdir=$(cd "$(dirname "$0")" && pwd)

if [ $PYTHON_VERSION == "3.4" ] || [ $PYTHON_VERSION == "3.5" ] || [ $PYTHON_VERSION == "3.6" ]
then
	echo "BUILDING BOOST for PYTHON $PYTHON_VERSION"
	deps="boost-python3"
else
	echo "INSTALL BOOST for PYTHON $PYTHON_VERSION"
	deps="boost-python"
fi 

deps_install ()
{
	# install all dependent libraries for azure-iot-sdk-c
	brew install boost openssl cmake

	if brew list boost-python >/dev/null 2>&1; then
		echo "Reinstall boost-python"
		brew uninstall boost-python
	fi
	brew install $deps
}

deps_install

