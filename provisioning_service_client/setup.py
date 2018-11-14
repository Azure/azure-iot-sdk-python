from setuptools import setup, Distribution
import sys

with open("doc/package-readme.md", "r") as fh:
    _long_description = fh.read()

try:
    if sys.version_info < (2, 7):
        raise PlatformError("Require Python 2.7 or greater")
    if sys.version_info >= (3, 0) and sys.version_info < (3, 4):
        raise PlatformError("Require Python 3.4 or greater")
except PlatformError as e:
    sys.exit(e.value)

setup(
    name='azure_iothub_provisioningserviceclient',
    version='1.1.0',
    description='IoT Hub Provisioning Service Client Library',
    license='Apache Software License',
    url='https://github.com/Azure/azure-iot-sdk-python/tree/master/provisioning_service_client',
    author='aziotclb',
    author_email='aziotclb@microsoft.com',
    long_description=_long_description,
    long_description_content_type='text/markdown',
    install_requires=['msrest'],
    packages=['provisioningserviceclient', 'provisioningserviceclient.protocol', 'provisioningserviceclient.protocol.models', 'provisioningserviceclient.protocol.operations', 'provisioningserviceclient.utils'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'],
)
