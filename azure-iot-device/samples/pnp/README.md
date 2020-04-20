# Python PNP Sample

 
### Prerequisites:  

Python 3.5+ preferably Python 3.7. You can check your python version by running  

```commandline
python --version
```

#### Execute Sample via Python V2 SDK install 

Navigate to your Workspace. You can additionally create another folder called __pnp__ inside your workspace. 

```commandline
pip install azure-iot-device
```


We can use __wget__ to copy the files over from Github directly.  

 
```commandline
wget https://raw.githubusercontent.com/Azure/azure-iot-sdk-python/digitaltwins-preview/azure-iot-device/samples/pnp/pnp_helper.py 
wget https://raw.githubusercontent.com/Azure/azure-iot-sdk-python/digitaltwins-preview/azure-iot-device/samples/pnp/pnp_methods.py 
wget https://raw.githubusercontent.com/Azure/azure-iot-sdk-python/digitaltwins-preview/azure-iot-device/samples/pnp/pnp_environmental_monitor.py 
```

You can also copy over the files physically to your working folder. The location to get the files are in: -  https://github.com/Azure/azure-iot-sdk-python/tree/digitaltwins-preview/azure-iot-device/samples/pnp 

Take a moment to examine the code in the folder __pnp__. There are 3 files in this folder.  

1. pnp_environmental_monitor.py
2. pnp_helper.py 
3. pnp_methods.py 

The sample file is __pnp_environmental_monitor.py__. Notice that the sample uses methods from __pnp_methods.py__. This __pnp_methods.py__ file uses our __azure-iot-device__ SDK functionality to provide PNP compatible functionality. It uses certain helper functions that are present in the __pnp_helper.py__ file.  Where are the interfaces or dtdl ? 

Now look at __pnp_environmental_monitor.py__ Notice how: 

* pnp_methods have been imported to enable utilization of their functions. 

* The capability model is defined at the top. This must be known to the user and can be found from DTDL. 

* Some command handlers are written. These are user written handlers and functionality can be changed according to what the user wants to do after receiving command requests. 

* An input keyboard listener is written. This is only to quit the application. 

* After that the main functionality starts. The main functionality includes creation of the client, listeners for command requests, an update property task and a send telemetry task. 

    * The first step is to create the device client using the device SDK supplying the connection string. 

    * The __execute_listener__ method is defined in pnp_methods which listens to command requests. All the user needs to pass as parameters are the client, device name, the method name and the user handler.  

    * The __pnp_update_property__ is defined in pnp_methods which updates properties for the device. The user needs to pass the client, the interface and the properties in key value pattern. 

    * The __pnp_send_telemetry__ is also defined in pnp_methods which sends telemetry. The user needs to use this one in a loop to send telemetry at certain interval (8 secs in sample) 

* Once all the functionality is done, all the listeners and tasks are disabled. 


Use the IoT Hub you've created and use the device that you have in the hub. 
Copy its connection string in an environment variable named: IOTHUB_DEVICE_CONNECTION_STRING

After you have a feel for the code, go ahead and run the sample with: 


```commandline
python pnp_environmental_monitor.py
```

This will complete all the above-mentioned steps, and now the device is sending telemetry messages every 8 seconds to your hub. You can verify this by monitoring events on the hub. For example, open a Cloudshell cmd line in Azure portal and type: 

`az extension add --name azure-cli-iot-ext`

`az iot hub monitor-events --hub-name <your hub name>`

## Writing your own sample

For writing your own sample for a PNP enabled device what the user needs to know and edit in the already existing sample are:-

1. capability model
2. interface name
3. device name
4. the commands that the device wants to listen to
    * the associated handlers that the user wants to execute after command reception.
4. specific properties of the device that needs to be reported and their corresponding values
5. telemetry messages that the user wants to send.


These are the only things that needs to be supplied by the user. All the messages, properties will be formatted by our pnp methods and helpers.
