@REM Copyright (c) Microsoft. All rights reserved.
@REM Licensed under the MIT license. See LICENSE file in the project root for full license information.

@echo off

rem ensure python.exe exists
where /q python.exe
if errorlevel 1 goto :NeedPython

python python_version_check.py >pyenv.bat
if errorlevel 1 goto :NeedPython

call pyenv.bat

@setlocal EnableExtensions EnableDelayedExpansion

set build-root=%~dp0
rem // resolve to fully qualified path
for %%i in ("%build-root%") do set build-root=%%~fi
cd %build-root%

rem -----------------------------------------------------------------------------
rem -- check prerequisites
rem -----------------------------------------------------------------------------

rem -----------------------------------------------------------------------------
rem -- detect Python x86 or x64 version, select build target accordingly
rem -----------------------------------------------------------------------------

REM target may be set to 64 bit build if a Python x64 detected
set build-config=Release
set wheel=0
set platname=win32
set use_tpm_simulator=

goto :args-loop

:NeedPython
@Echo Azure IoT SDK needs Python 2.7 or Python 3.4 from 
@Echo https://www.python.org/downloads/
exit /b 1

:args-loop
if "%1" equ "" goto args-done
if "%1" equ "--config" goto arg-build-config
if "%1" equ "--wheel" goto arg-build-wheel
if "%1" equ "--platform" goto arg-build-platform
if "%1" equ "--use-tpm-simulator" goto arg-use-tpm-simulator
call :usage && exit /b 1

:arg-build-config
shift
if "%1" equ "" call :usage && exit /b 1
set build-config=%1
goto args-continue

:arg-build-wheel
set wheel=1
goto args-continue

:arg-build-platform
shift
if "%1" equ "" call :usage && exit /b 1
set build-platform=%1
goto args-continue

:arg-use-tpm-simulator
set use_tpm_simulator=--use-tpm-simulator
goto args-continue

:args-continue
shift
goto args-loop

:args-done

:build

@Echo Using Python found in: %PYTHON_PATH%, building Python %build-python% %build-platform% extension

set cmake-output=cmake_%build-platform%

REM -- C --
cd %build-root%..\..\c\build_all\windows

call build_client.cmd --platform %build-platform% --buildpython %build-python% --config %build-config% --provisioning %use_tpm_simulator% --use_edge_modules

if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
cd %build-root%

@Echo CMAKE Output Path: %USERPROFILE%\%cmake-output%\python

copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pyd ..\..\device\samples
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pyd ..\..\device\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python\test\%build-config%\iothub_client_mock.pyd ..\..\device\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pyd ..\..\service\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!

copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pyd ..\..\service\samples
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pyd ..\..\service\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python_service_client\tests\%build-config%\iothub_service_client_mock.pyd ..\..\service\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pyd ..\..\device\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!

copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\src\%build-config%\provisioning_device_client.pyd ..\..\provisioning_device_client\samples
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\src\%build-config%\provisioning_device_client.pyd ..\..\provisioning_device_client\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\tests\%build-config%\provisioning_device_client_mock.pyd ..\..\provisioning_device_client\tests
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!

if "%build-config%"=="Debug" (
    copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pdb ..\..\device\samples
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pdb ..\..\device\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python\test\%build-config%\iothub_client_mock.pdb ..\..\device\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pdb ..\..\service\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!

    copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pdb ..\..\service\samples
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pdb ..\..\service\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python_service_client\tests\%build-config%\iothub_service_client_mock.pdb ..\..\service\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pdb ..\..\device\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!

    copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\src\%build-config%\provisioning_device_client.pdb ..\..\provisioning_device_client\samples
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\src\%build-config%\provisioning_device_client.pdb ..\..\provisioning_device_client\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\tests\%build-config%\provisioning_device_client_mock.pdb ..\..\provisioning_device_client\tests
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
)

cd ..\..\device\tests
@Echo python iothub_client_ut.py
python -u iothub_client_ut.py
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
@Echo python iothub_client_map_test.py
python -u iothub_client_map_test.py
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
echo Python unit test PASSED
cd %build-root%

cd ..\..\service\tests
@Echo python iothub_service_client_ut.py
python -u iothub_service_client_ut.py
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
@Echo python iothub_service_client_map_test.py
python -u iothub_service_client_map_test.py
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
echo Python unit test PASSED
cd %build-root%

cd ..\..\provisioning_device_client\tests
@Echo python provisioning_device_client_ut.py
python -u provisioning_device_client_ut.py
if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
echo Python unit test PASSED
cd %build-root%
)

rem -----------------------------------------------------------------------------
rem -- create PyPi wheel
rem -----------------------------------------------------------------------------

if "%build-platform%"=="x64" (
    set platname=win-amd64
)

if %wheel%==1 (
    cd %build-root%

    echo Copy iothub_client.pyd to %build-root%\build_all\windows\iothub_client for IoTHub Device Client Python wheel generation
    copy %USERPROFILE%\%cmake-output%\python\src\%build-config%\iothub_client.pyd ..\..\build_all\windows\release_device_client\iothub_client
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    echo update Python packages
    python -m pip install -U pip setuptools wheel twine
    echo create Python wheel:
    echo "python setup_device_client.py bdist_wheel --plat-name %platname%"
    cd release_device_client
    python setup_device_client.py bdist_wheel --plat-name "%platname%"
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    dir dist
    echo IoTHub Device Client Python wheel done

    cd %build-root%
    echo Copy iothub_service_client.pyd to %build-root%\build_all\windows\iothub_service_client for IoTHub Service Client Python wheel generation
    copy %USERPROFILE%\%cmake-output%\python_service_client\src\%build-config%\iothub_service_client.pyd ..\..\build_all\windows\release_service_client\iothub_service_client
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    echo update Python packages
    python -m pip install -U pip setuptools wheel twine
    echo create Python wheel:
    echo "python setup_service_client.py bdist_wheel --plat-name %platname%"
    cd release_service_client
    python setup_service_client.py bdist_wheel --plat-name "%platname%"
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    dir dist
    echo IoTHub Service Client Python wheel done

    cd %build-root%
    echo Copy provisioning_device_client.pyd to %build-root%\build_all\windows\provisioning_device_client for IoT Provisiomomg Device Client Python wheel generation
    copy %USERPROFILE%\%cmake-output%\provisioning_device_client_python\src\%build-config%\provisioning_device_client.pyd ..\..\build_all\windows\release_provisioning_device_client\provisioning_device_client
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    echo update Python packages
    python -m pip install -U pip setuptools wheel twine
    echo create Python wheel: 
    echo "python provisioning_device_client.py bdist_wheel --plat-name %platname%"
    cd release_provisioning_device_client
    python setup_provisioning_device_client.py bdist_wheel --plat-name "%platname%"
    if not !ERRORLEVEL!==0 exit /b !ERRORLEVEL!
    dir dist
    echo IoT Provisioning Device Client Python wheel done

    cd %build-root%
)
goto :eof

:usage
echo build_client.cmd [options]
echo options:
echo  --config ^<value^>         [Debug] build configuration (e.g. Debug, Release)
echo  --platform ^<value^>       [Win32] build platform (e.g. Win32, x64, ...)
echo  --buildpython ^<value^>    [2.7]   build python extension (e.g. 2.7, 3.4, ...)
echo  --no-logging               Disable logging
echo  --use-tpm-simulator        Build TPM simulator
goto :eof
