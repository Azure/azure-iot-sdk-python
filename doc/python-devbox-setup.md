# Prepare your development environment

This document describes how to prepare your development environment to use the *Microsoft Azure IoT SDKs for Python*.

- [Setup your development environment](#devenv)
- [Install the Python modules using PyPI wheels](#pypi-wheels)
- [Build the samples on Linux](#linux)
- [Build the samples on Mac](#mac)
- [Build the samples on Windows using nuget packages](#windows)
- [Build the samples on Windows using cmake and boost libraries](#windows-cmake)
- [Sample applications](#samplecode)

<a name="devenv"></a>
## Setup your development environment

Ensure that the desired Python version is installed (2.7.x, 3.4.x or 3.5.x). Run `python --version` or `python3 --version` at the command line to check the version. 
* On Linux, Python 2.7 is typically already installed and active. 
* On Windows, install the latest x86 or x64 Python 2.7 or 3.x client from ([python.org](https://www.python.org/downloads/)). If you plan to build the Python library, the scrips will need a valid Python.exe in the path. Based on the active Python version (e.g. Python 2.7.11 x86 32bit) the build script choses the compiler settings for the Python extension module build accordingly and copies the extension to the test and sample folders.

<a name="pypi-wheels"></a>
## Install the Python modules using PyPI wheels from [PyPI] 

1. Open a command-prompt (Windows) or console (other platforms) window.
2. To install the Azure IoT Hub device client module (**iothub\_client** package), type the following command: `pip install azure-iothub-device-client`
3. To install the Azure IoT Hub service client module (**iothub\_service\_client** package), type the following command: `pip install azure-iothub-service-client`
4. Now Python is ready to run your application. 

> Notes: 
> - Supported platforms: Windows, Linux (Ubuntu), Raspberry Pi
> - On Windows make sure the Visual C++ Redistributable for Visual Studio 2015 package is installed from here: https://www.microsoft.com/en-us/download/details.aspx?id=48145 (Note: Visual Studio 2015 installation includes it) 
> - On other platforms make sure the Pip tool is upgraded to the latest version. (> 9)
> - If Pip cannot install the package for the specific version of Python installed on your machine, use one of the following options to build the **iothub_client** module.

<a name="linux"></a>
## Build the Azure IoT Hub SDKs for Python on Linux

### Installs needed to compile the SDKs for Python from souce code
Because the Azure IoT SDKs for Python are wrappers on top of the [SDKs for C][azure-iot-sdk-c], you will need to compile the C libraries if you want or need to generate the Python libraries from source code.
You will notice that the C SDKs are brought in as submodules to the current repository.
In order to setup your development environment to build the C binaries make sure all dependencies are installed before building the SDK. 

1. Clone the Azure IoT Python SDK Repo

    ```
    git clone --recursive https://github.com/Azure/azure-iot-sdk-python.git 
    ```

2. For Ubuntu, you can use apt-get to install the right packages:
  
    ```
    sudo apt-get update
    sudo apt-get install -y git cmake build-essential curl libcurl4-openssl-dev libssl-dev uuid-dev
    ```

3. Verify that CMake is at least version **2.8.12**:
  
    ```
    cmake --version
    ```
  
    > For information about how to upgrade your version of CMake to 3.x on Ubuntu 14.04, read [How to install CMake 3.2 on Ubuntu 14.04?](http://askubuntu.com/questions/610291/how-to-install-cmake-3-2-on-ubuntu-14-04).

4. Verify that gcc is at least version **4.4.7**:
  
    ```
    gcc --version
    ```
  
    > For information about how to upgrade your version of gcc on Ubuntu 14.04, read [How do I use the latest GCC 4.9 on Ubuntu 14.04?](http://askubuntu.com/questions/466651/how-do-i-use-the-latest-gcc-4-9-on-ubuntu-14-04).

### Compile the Python modules
The Python iothub_client and iothub_service_client modules support python versions 2.7.x, 3.4.x, 3.5.x or 3.6.x. Know the appropriate version you would like to build the library with for the following instructions.

1. Clone the Azure IoT Python SDK Repo
  
    ```
    git clone --recursive https://github.com/Azure/azure-iot-sdk-python.git 
    ```

1. Ensure that the desired Python version (2.7.x, 3.4.x, 3.5.x or 3.6.x) is installed and active. Run `python --version` or `python3 --version` at the command line to check the version.
1. Open a shell and navigate to the folder **build_all/linux** in your local copy of the repository.
1. Run the `./setup.sh` script to install the prerequisite packages and the dependent libraries.
    * Setup will default to python 2.7
    * To setup dependencies for python version greater than 3, run `./setup.sh --python-version X.Y` where "X.Y" is the python version (e.g. 3.4, 3.5 or 3.6)
1. Run the `./build.sh` script.
    * Build will default to python 2.7
    * To build with python version greater than 3, run `./build.sh --build-python X.X` where "X.Y" is the python version (e.g. 3.4, 3.5 or 3.6)
1. After a successful build, the `iothub_client.so` Python extension module is copied to the [**device/samples**][device-samples] and [**service/samples**][service-samples] folders. Visit these folders for instructions on how to run the samples.

### Known build issues: 

1. When building the Python client library (`iothub_client.so`) on Linux devices that have less than **1GB** RAM, you may see build getting **stuck** at **98%** while building `iothub_client_python.cpp` as shown below

``[ 98%] Building CXX object python/src/CMakeFiles/iothub_client_python.dir/iothub_client_python.cpp.o``

If you run into this issue, check the **memory consumption** of the device using `free -m command` in another terminal window during that time. If you are running out of memory while compiling iothub_client_python.cpp file, you may have to temporarily increase the **swap space** to get more available memory to successfully build the Python client side device SDK library.

1. CentOS7: Only Python 2.7 is supported due to a missing boost-python3 library package

<a name="mac"></a>
## Build the Azure IoT Hub SDKs for Python on Mac OS

### Installs needed to compile the SDKs for Python from souce code
Because the Azure IoT SDKs for Python are wrappers on top of the [SDKs for C][azure-iot-sdk-c], you will need to compile the C libraries if you want or need to generate the Python libraries from source code.
You will notice that the C SDKs are brought in as submodules to the current repository.
In order to setup your development environment to build the C binaries, you need to follow the instructions [here][c-devbox-setup]:
* On Mac OS you will need XCode and install the Commandline Utils

### Compile the Python modules
The Python iothub_client and iothub_service_client modules support python versions 2.7.x, 3.4.x, 3.5.x or 3.6.x. Know the appropriate version you would like to build the library with for the following instructions.

1. Clone the Azure IoT Python SDK Repo
  
    ```
    git clone --recursive https://github.com/Azure/azure-iot-sdk-python.git 
    ```

1. Ensure that the desired Python version (2.7.x, 3.4.x, 3.5.x or 3.6.x) is installed and active. Run `python --version` or `python3 --version` at the command line to check the version.
1. Open a shell and navigate to the folder **build_all/mac** in your local copy of the repository.
1. Run the `./setup.sh` script to install the prerequisite packages and the dependent libraries.
    * Setup will default to python 2.7
    * To setup dependencies for python version greater than 3, run `./setup.sh --python-version X.Y` where "X.Y" is the python version (e.g. 3.4, 3.5 or 3.6)
1. Run the `./build.sh` script.
    * Build will default to python 2.7
    * To build with python version greater than 3, run `./build.sh --build-python X.X` where "X.Y" is the python version (e.g. 3.4, 3.5 or 3.6) 
1. After a successful build, the `iothub_client.so` Python extension module is copied to the [**device/samples**][device-samples] and [**service/samples**][service-samples] folders. Visit these folders for instructions on how to run the samples.

### Known build issues: 

None

<a name="windows"></a>
## Build the Python device and service client modules on Windows using Nuget packages (recommended)

### Prerequisite
Because the Azure IoT SDKs for Python are wrappers on top of the [SDKs for C][azure-iot-sdk-c], you will need to compile the C libraries if you want or need to generate the Python libraries from source code.
You will notice that the C SDKs are brought in as submodules to the current repository.
In order to setup your development environment to build the C binaries, you need to follow the instructions [here][c-devbox-setup]:
* On Windows you will need Visual Studio and git

### Compile the Python modules in Visual Studio
1. Open a Visual Studio 2015 x86 Native Tools command prompt and navigate to the folder **build_all/windows** in your local copy of the repository.
2. Run the script `build.cmd` in the **build_all\\windows** directory.
3. As a result, the `iothub_client.pyd` Python extension module is copied to the **device/samples** folder. Follow the instructions in [Sample applications](#samplecode) to run the Python IoT Hub samples.
4. In order to run the samples with a different Python version (e.g. 32bit vs. 64bit or 2.7 vs. 3.4) please rebuild the `iothub_client.pyd` extension.

<a name="windows-cmake"></a>
## Build the Python device and service client modules on Windows using cmake and boost libraries 

### Prerequisite
Because the Azure IoT SDKs for Python are wrappers on top of the [SDKs for C][azure-iot-sdk-c], you will need to compile the C libraries if you want or need to generate the Python libraries from source code.
You will notice that the C SDKs are brought in as submodules to the current repository.
In order to setup your development environment to build the C binaries, you need to follow the instructions [here][c-devbox-setup]:
* On Windows you will need Visual Studio, git and cmake

### Compile the Python modules using boost::python libraries in Windows. 
1. Open a Visual Studio 2015 x86 or x64 Native Tools command prompt, depending on your installed Python version.
2. Download the zip version of the boost 1.60 library for windows from [boost-zip]. 
3. Unpack zip to a local folder, e.g. **C:\boost_1_60_0**.
4. Navigate to the root folder of the boost library, e.g. **C:\boost_1_60_0**.
5. Run the script `bootstrap.bat` in the boost folder.
6. At this point the desired Python version (e.g. V3.4 64bit) must be installed and active in the `PATH` environment variable.
7. Run the build command `b2` in the same folder. For x64 builds use the build command `b2 address-model=64`.
8. Set the environment variable **BOOST_ROOT** to the boost folder using the command `SET BOOST_ROOT=C:\boost_1_60_0`.

> Now the boost::python library is ready for use. 

> Important note: The boost libraries can only be used to build for a single Python version (e.g. V3.4 64bit). In order to build with cmake for another Python version, a clean bootstrap and build of the boost libraries for that version is necessary, or build errors will occur. It is possible to have multiple boost libraries for different Python versions side by side in different roots. Then the **BOOST_ROOT** folder must point to the appropriate boost library at cmake build time.

9. Open a Visual Studio 2015 x86 Native Tools command prompt and navigate to the folder **build_all/windows** in your local copy of the repository.
10. Verify that `BOOST_ROOT` points to the local boost installation for the right Python version.
11. Run the script `build_client.cmd` in the **build_all\\windows** directory.
12. After a successful build, the `iothub_client.pyd` Python extension module is copied to the **device/samples** folder. Please follow instructions in [Sample applications](#samplecode) to run the Python samples.

To use the iothub_client and iothub_service_client extensions for native code debugging with [Python Tools for Visual Studio] run the script: `build_client.cmd --config Debug` to get the full debug symbol support.

<a name="samplecode"></a>
## Sample applications

This repository contains various Python sample applications that illustrate how to use the Microsoft Azure IoT SDKs for Python.
* [Samples showing how to use the Azure IoT Hub device client][device-samples]
* [Samples showing how to use the Azure IoT Hub service client][service-samples]


[python-2.7 or python-3.5]: https://www.python.org/downloads/
[PyPI]: https://pypi.python.org/pypi/azure-iothub-device-client/
[PyPi]: https://pypi.python.org/pypi/azure-iothub-service-client
[Python Tools for Visual Studio]: https://www.visualstudio.com/en-us/features/python-vs.aspx
[device-samples]: ../device/samples/
[service-samples]: ../service/samples/

[boost-zip]: http://www.boost.org/users/history/version_1_60_0.html
[azure-iot-sdk-c]: https://github.com/azure/azure-iot-sdk-c
[c-devbox-setup]: https://github.com/Azure/azure-iot-sdk-c/blob/master/doc/devbox_setup.md
