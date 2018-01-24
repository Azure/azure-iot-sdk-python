from setuptools import setup, Distribution
import sys

setup(
    name='azure_iothub_provisioningserviceclient',
    version='0.0.1',
    description='IoT Hub Provisioning Service Client Library',
    license='Apache Software License',
    url='https://github.com/Azure/azure-iot-sdk-python/tree/master/provisioningserviceclient',
    author='aziotclb',
    author_email='aziotclb@microsoft.com',
    long_description='IoT Hub Provisioning Service Client Library for Python',
    install_requires=['msrest'],
    packages=['provisioningserviceclient', 'provisioningserviceclient.serviceswagger', 'provisioningserviceclient.serviceswagger.models', 'provisioningserviceclient.serviceswagger.operations'],
    classifiers=[
        'Development Status :: 3 - Alpha',
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
