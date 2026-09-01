# Prepare your development environment

This document describes how to prepare your development environment to work with the Microsoft Azure IoT Device SDK for Python.

## End User
If you are simply using the Microsoft Azure IoT SDK for Python as an end user and do not need to modify the code itself, you can simply install the package via `pip` as follows:

```console
pip install azure-iot-device
```

## IoT Device SDK developer
Development uses [uv](https://docs.astral.sh/uv/) to install Python versions, create the project virtual environment, and reproduce dependencies from `uv.lock`.

Install uv, then run these commands from the repository root:

```console
uv sync
uv run pre-commit install
```

`uv sync` installs the SDK and all development dependency groups into `.venv`. Source changes are immediately reflected because the SDK and `dev_utils` are installed editably.

The checked-in `uv.lock` provides a reproducible contributor environment. Cached Azure Pipelines E2E jobs deliberately resolve an upgraded lockfile before caching, then run `uv sync --locked` so the library is tested against the newest compatible dependencies without changing the cache key during a job.

Common commands:

```console
uv run pytest tests
uv run ruff check .
uv run black path/to/file.py
uv build
```

To test with another supported Python version, install it with `uv python install 3.10` and recreate the environment with `uv sync --python 3.10`. CI runs the complete Python 3.10 through 3.14 matrix.

## Environment Variables (Optional)

If you wish to follow the samples exactly as written, you will need to set some environment variables on your system. These are not required however - if you wish to use different environment variables, or no environment variables at all, simply change the samples to retrieve these values from elsewhere. Additionally, different samples use different variables, so you would only need the ones relevant to samples you intend to use.

### Connection String Device Authentication
* **IOTHUB_DEVICE_CONNECTION_STRING**: The connection string for your IoTHub Device, which can be found in the Azure Portal

### X509 Authentication
* **X509_CERT_FILE**: The path to the X509 certificate
* **X509_KEY_FILE**: The path to the X509 key
* **X509_PASS_PHRASE**: The pass phrase for the X509 key (Only necessary if cert has a password)

**This is an incomplete list of environment variables**