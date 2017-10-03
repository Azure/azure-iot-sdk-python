# Cross Compiling Azure IoT SDK for Python Example
## Overview

The goal of this document is to describe the steps required to cross compile the Azure IoT SDK for Python in order to allow the user to use Python to send and receive messages between the device and one&#39;s Azure IoT Hub. For this example, the target device will be the [MultiTech device](https://catalog.azureiotsuite.com/details?title=MultiConnect-Conduit&amp;source=home-page). It will describe how to install the compiler toolchain for the this device, build the required prerequisite software and finally cross compile the Azure IoT SDK for Python library. The procedure for other Linux based target devices should be very similar.

This process will consist of three tasks:

1. Download and install the MultiTech toolchain
2. Download and build the Boost library against the MultiTech toolchain
3. Download and build the Azure IoT SDK for Python against the MultiTech toolchain

All commands will assume that you are starting with your current directory at your home directory. If you keep the directories names and relative locations the same as described this will save you from editing files later in the process. To switch to your home directory enter:
```
cd ~
```
### Assumptions

You are building the software on an Ubuntu distribution. For the purposes of testing this document I used Ubuntu 16.04 64-bit.

You are a member of the sudo user group. You will only need to use sudo to install prerequisite software. All other steps can (and should) be performed as a standard user.

### Prerequisites

You will require a working Python installation before starting this process. Typically, most Linux distributions have Python installed out of the box.

Other required software:

- gcc – the C compiler
- g++ – the C++ compiler
- cmake – application used to generate build files
- git – used to clone repositories from GitHub.com
- curl - library is referenced by the SDK
- openssl - libraries are referenced by the SDK

Install these packages with:
```
sudo apt-get install cmake git build-essential curl libcurl4-openssl-dev libssl-dev uuid-dev
```
### Editing Files

You will need to create two files and modify one file during the course of this procedure. If you are using Ubuntu, then the simplest editor to use is nano. For example, if you wish to create a new file in your current directory simply type:
```
nano mynewfile
```
When you have completed your edits, press ctrl-o, press enter to save with the original file name and press ctrl-x to exit the editor. To edit an existing file simply replace _mynewfile_ with its name.

## Step 1: Install the MultiTech toolchain

The required toolchain can be found at MultiTech&#39;s website [here](http://www.multitech.net/developer/software/mlinux/mlinux-software-development/mlinux-c-toolchain/). We will need to download and install this toolchain to use it in later steps. The webpage contains detailed instructions on how to do that but, for convenience, we will document them here too.
```
curl http://www.multitech.net/mlinux/sdk/3.3.6/mlinux-eglibc-x86\_64-mlinux-factory-image-arm926ejste-toolchain-3.3.6.sh &gt; mlinux-toolchain-install.sh
```
The SDK is around 420Mb so it will take a while to download.

Now modify the downloaded file to be a Linux executable and run it to install the toolchain. In this instance we are overriding the default install location with the -d option to a directory in our home directory. We&#39;ve also added the -y flag to have it automatically reply yes to any questions. This will take a few minutes.
```
chmod +x mlinux-toolchain-install.sh

./mlinux-toolchain-install.sh -d ~/mlinux/3.3.6 -y
```
This concludes the installation of the MultiTech toolchain.

## Step 2: Acquire and Build the Boost Library

The Boost library is required for the Azure IoT SDK for Python. It provides several helper functions that ease the development of a binary Python library. The Python SDK utilizes these to provide a Python compatible binary that wraps the standard C SDK. The Boost library will need to be built from source code.

Start by downloading the source archive from the Boost webpage and unpacking it:
```
wget https://dl.bintray.com/boostorg/release/1.64.0/source/boost_1_64_0.tar.gz

tar -xzf boost_1_64_0.tar.gz
```
This will also take a few minutes to complete.

Now we need to run the Boost configuration script which tells the Boost build system what we want to build.
```
cd boost_1_64_0

./bootstrap.sh --with-libraries=python –-prefix=${HOME}/boostmlinux-1-64-0
```
At this point we need to modify the file _project-config.jam_ to tell the Boost build system to use our MultiTech cross compile toolchain when we build it. To do this, with an editor of your choice, nano, vim, WinSCP, etc., (see Editing Files above) open this file and make the following modifications indicated below. **Note:** Do not copy and paste the entire text below. The bootstrap command generates absolute paths in this file. These must not be replaced.
```
# Boost.Build Configuration
# Automatically generated by bootstrap.sh

import option ;
import feature ;
import os ;                              ### Add this line

local HOME = [ os.environ HOME ] ;       ### Add this line

# Compiler configuration. This definition will be used unless
# you already have defined some toolsets in your user-config.jam
# file.

### Modify the gcc section to use the cross compiler toolchain
if ! gcc in [ feature.values <toolset> ]
{
    using gcc
          : arm
          : $(HOME)/mlinux/3.3.6/sysroots/x86\_64-mlinux-linux/usr/bin/arm-mlinux-linux-gnueabi/arm-mlinux-linux-gnueabi-g++
          : <compileflags> "-v --sysroot=$(HOME)/mlinux/3.3.6/sysroots/arm926ejste-mlinux-linux-gnueabi -L$(HOME)/mlinux/3.3.6/sysroots/arm926ejste-mlinux-linux-gnueabi/usr/lib"
          ;
}

project : default-build <toolset>gcc ;

# Python configuration

import python ;

### Modify this section to reflect your Python location and version
if ! [ python.configured ]
{
     using python
           : 2.7
           : $(HOME)/mlinux/3.3.6/sysroots/arm926ejste-mlinux-linux-gnueabi/usr/bin
           : $(HOME)/mlinux/3.3.6/sysroots/arm926ejste-mlinux-linux-gnueabi/usr/include/python2.7
           : $(HOME)/mlinux/3.3.6/sysroots/arm926ejste-mlinux-linux-gnueabi/usr/lib
           ;
}

# List of --with-<library> and --without-<library>
# options. If left empty, all libraries will be built.
# Options specified on the command line completely
# override this variable.

libraries =  --with-python ;

# These settings are equivivalent to corresponding command-line
# options.

option.set prefix : /home/markrad/boostmlinux-1-64-0 ;
option.set exec-prefix : /home/markrad/boostmlinux-1-64-0 ;
option.set libdir : /home/markrad/boostmlinux-1-64-0/lib ;
option.set includedir : /home/markrad/boostmlinux-1-64-0/include ;

# Stop on first error

option.set keep-going : false ;
```
Figure 1: Modified project-config.jam

Build Boost for your MultiTech with the following command:
```
./b2 toolset=gcc-arm --build-dir=${HOME}/boost-build-dir link=static install
```
After this process is complete you will have a new directory in your home directory called boostmlinux-1-64-0 containing a lib and include directory.

## Step 3: Build the Python SDK for a MultiTech Device

Once again, starting from your home directory, clone the Azure IoT SDK for Python with the following command:
```
git clone --recursive https://github.com/azure/azure-iot-sdk-python.git
```
Now execute the following commands:
```
cd azure-iot-sdk-python

mkdir cmake

cd build_all/linux
```
You will need to create two files in this directory. With the editor of your choice first create _toolchain-mlinux.cmake_. Into this file enter the following:
```cmake
INCLUDE (CMakeForceCompiler)
SET (CMAKE_SYSTEM_NAME Linux)     # this one is important
SET (CMAKE_SYSTEM_VERSION 1)      # this one not so much

# Set up some paths for the build
SET (CMAKE_SYSROOT $ENV{ML_SYSROOT})
SET (CMAKE_LIBRARY_PATH "$ENV{ML_SYSROOT}/usr/lib")
SET (CMAKE_PREFIX_PATH "$ENV{ML_SYSROOT}/usr")
SET (Boost_INCLUDE_DIR "$ENV{BOOST_ROOT}/include")
SET (Boost_LIBRARY_DIR_RELEASE "$ENV{BOOST\_ROOT}/lib")

# Uncomment for a little debug info
#message("Boost_INCLUDE_DIR ${Boost_INCLUDE_DIR}")
#message("Boost_LIBRARY_DIR_RELEASE ${Boost_LIBRARY_DIR_RELEASE}")

# Set up the compilers and the flags
SET (CMAKE_C_COMPILER $ENV{ML_HOSTTOOLS}/arm-mlinux-linux-gnueabi/arm-mlinux-linux-gnueabi-gcc)
SET (CMAKE_CXX_COMPILER $ENV{ML_HOSTTOOLS}/arm-mlinux-linux-gnueabi/arm-mlinux-linux-gnueabi-g++)
SET (CMAKE_C_FLAGS "-march=armv5te -marm -mthumb-interwork -mtune=arm926ej-s -Wl,-O1 -Wl,--hash-style=gnu -Wl,--as-needed")
SET (CMAKE_CXX_FLAGS "-march=armv5te -marm -mthumb-interwork -mtune=arm926ej-s -Wl,-O1 -Wl,--hash-style=gnu -Wl,--as-needed")

# This is the file system root of the target
SET (CMAKE_FIND_ROOT_PATH $ENV{ML_SYSROOT})

# Search for programs in the build host directories
SET (CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# For libraries and headers in the target directories
SET (CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)

SET (CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
```
<div style="text-align: center; font-size: smaller">Figure 2: CMake toolchain file</div>

Create a second file called _mlinuxenv.sh_ and into it enter the following:
```bash
export ML_TOOLCHAINROOT=${HOME}/mlinux/3.3.6/sysroots
export ML_HOSTTOOLS=${ML_TOOLCHAINROOT}/x86\_64-mlinux-linux/usr/bin
export ML_SYSROOT=${ML_TOOLCHAINROOT}/arm926ejste-mlinux-linux-gnueabi
export BOOST_ROOT=${HOME}/boostmlinux-1-64-0
export PATH=${ML_HOSTTOOLS}/bin:${ML_HOSTTOOLS}/bin/arm-mlinux-linux-gnueabi:$PATH

cmake -DCMAKE_INSTALL_PREFIX=~/mlinux-out -DCMAKE_TOOLCHAIN_FILE=../build_all/linux/toolchain-mlinux.cmake ..
```
<div style="text-align: center; font-size: smaller">Figure 3: Build Generator Script</div>

Having created the two files, we are now ready to build the SDK. Enter the following commands:
```
chmod a+x mlinuxenv.sh
cd ../../cmake
../build_all/linux/mlinuxenv.sh
make install
```
This will build the SDK and create the Python library. To check that the binary Python library has been built correctly enter:
```
file ~/mlinux-out/lib/*.so
```
This should result in two lines of output, one for _iothub\_client.so_ and one for _iothub\_service\_client.so_. The details should say that they are _ELF 32-bit LSB shared object, ARM, EABI5 version 1 (SYSV), dynamically linked_ which is the appropriate architecture for your target machine.

## Conclusion

This document has described the procedure to cross compile the Azure IoT SDK binary Python library targeting a MultiTech device.

Additionally, I have tested this procedure in a Windows Subsystem for Linux bash prompt successfully. This allows one to complete these steps without requiring an actual installation of Ubuntu. There is just one additional step you will need to take to use the Windows Subsystem for Linux. After you have installed the prerequisite software, run the command:
```
sudo ln -s /usr/bin/python2.7 /usr/bin/python
```
This will set up a soft symbolic link called python which is the command name the tools will expect to find.
