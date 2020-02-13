
# Command Object?

## Python
```
async def blink_command_listener(command):
    while True:
        command_request = await command.receive()

        print("Got the blink command")

        command_acknowledge = CommandAcknowledge.create_from_command_request(
            command_request, 200, "blink response"
        )
        try:
            await command.send_acknowledge(command_acknowledge)
        except Exception:
            print("responding to the blink command failed")

async def turn_on_command_listener(command):
    pass

async def turn_off_command_listener(command):
    pass

async def run_diagnostic_command_listener(command):
    while True:
        command_request = await command.receive()

        print("Got the runDiagnostics command.")

        command_acknowledge = CommandAcknowledge.create_from_command_request(
            command_request, 200, "runDiagnostics response"
        )
        try:
            await command.send_acknowledge(command_acknowledge)
        except Exception as e:
            print("responding to the runDiagnostics command failed: {}".format(e))
        else:
            command_update = CommandUpdate.create_from_command_request(
                command_request, 200, "runDiagnostics update response"
            )
            try:
                await command.send_update(command_update)
            except Exception as e:
                print("Got an error on the update: {}".format(e))


    listeners = asyncio.ensure_future(
        asyncio.gather(
            # new
            blink_command_listener(environmental_sensor.commands.blink),
            turn_on_command_listener(environmental_sensor.commands.turn_on),
            turn_off_command_listener(environmental_sensor.commands.turn_off),
            run_diagnostic_command_listener(environmental_sensor.commands.run_diagnostic),
            # others same as before
        )
    )
```

## Node

```

const environmentalSensor = new EnvironmentalSensor('environmentalSensor', environmentReadWriteCallback);   # remove callback

environmentalSensor.commands.blink.callback = (request: CommandRequest, response: CommandResponse) => {
  console.log('Got the blink command.');
  response.acknowledge(200, 'blink response', (err?: Error) => {
    if (err) {
      console.log('responding to the blink command failed.');
    }
  });
}

environmentalSensor.commands.turnOn.callback = (request: CommandRequest, response: CommandResponse) => {
  console.log('Got the turnOn command.');
  response.acknowledge(200, 'turn on response', (err?: Error) => {
    if (err) {
      console.log('responding to the turnOn command failed.');
    }
  });
}

environmentalSensor.commands.turnOff.callback = (request: CommandRequest, response: CommandResponse) => {
  console.log('Got the turnOff command.');
  response.acknowledge(200, 'turn off response', (err?: Error) => {
    if (err) {
      console.log('responding to the blink command failed.');
    }
  });
}

environmentalSensor.commands.runDiagnostics.callback = (request: CommandRequest, response: CommandResponse) => {
  console.log('Got the runDiagnostics command.');
  response.acknowledge(200, 'runDiagnostics response', (err?: Error) => {
    if (err) {
      console.log('responding to the runDiagnostics command failed ' + err.toString());
    }
    // response.update(200, 'runDiagnostics updated response', (updateError?: Error) => {
    //   if (updateError) {
    //     console.log('got an error on the update Response ' + updateError.toString());
    //   }
    // });
    response.update(200, 'runDiagnostics updated response')
       .then(() => {
        console.log('in the then for the update.');
       })
       .catch((err: Error) => {console.log('Got an error on the update: ' + err.toString());});
  });
}

```

# Telemetry object

## python
```
#  send telemetry every 5 seconds
def send_telemetry():
    while True:
        environmental_sensor.telemetry.temp = 10 + random.random_int(0, 90)
        environmental_sensor.telemetry.humid = 1 + random.randint(0, 99)
        await environmental_sensor.report_telemetry()   # uses setters amd dirty bits to know what to send
        await asyncio.sleep(5)

sender = asyncio.ensure_future(send_telemetry())
```

## could do the same with properties if the protocol supports this.
```
await environmental_sensor.properties.state = True
await environmental_sensor.report_properties()  # dirty bits again

device_information.properties.manufacturer = "Contoso Device Corporation"
device_information.properties.model = "Contoso 4762B-turbo"
device_information.properties.sw_version = "3.1"
device_information.properties.os_name = "ContosoOS"
device_information.properties.processor_architecture = "4762"
device_information.properties.processor_manufacturer = "Contoso Foundries"
device_information.properties.total_storage = "64000"
device_information.properties.total_memory = "640"
await device_information.report_properties()   # uses setters and dirty bits to know what to send
```

## In node
```
// Telemetry
setInterval( async () => {
    environmentalSensor.telemetry.temp = 10 + (Math.random() * 90);
    environmentalSensor.telemetry.humid = 1 + (Math.random() * 99);
    await environmentalSensor.sendTelemetry();
}, 5000);

// Properties
deviceInformation.properties.manufacturer = "Contoso Device Corporation"
deviceInformation.properties.model = "Contoso 4762B-turbo"
deviceInformation.properties.swVersion = "3.1"
deviceInformation.properties.osName = "ContosoOS"
deviceInformation.properties.processorArchitecture = "4762"
deviceInformation.properties.processorManufacturer = "Contoso Foundries"
deviceInformation.properties.totalStorage = "64000"
deviceInformation.properties.totalMemory = "640"
await deviceInformation.reportProperties()
```

# Property listeners using Property object:

# python
```
async def environmental_property_changed_listener(property):
    while True:
        # Note: this needs more thinking.  What data is in the property and what data is in the property_change object?
        property_change = await property.receive_property()

        try:
            # question: is the JSON blob below standard?  Should there be a model object for this?
            property.report(
                property_change.desired_value + "the boss",
                {
                    "responseVersion": property_change.version,
                    "statusCode": 200,
                    "statusDescription": "a promotion",
                },
            )
        except Exception:
            print("did not do the update")
        else:
            print("The update worked!!!!")

listeners = asyncio.ensure_future(
    asyncio.gather(
        # new.  Note how we use the same handler function for 2 different properties since this duplicates previous functionality.
        environmental_property_changed_listener(environmental_sensor.properties.name),
        environmental_property_changed_listener(environmental_sensor.properties.brighness),
        # others unchanged
    )
)
```

## node
```
environmental_sensors.properties.name.callback = (property: Property, oldDesiredValue: any, version: number) => {
    property.report(property.desired + ' the boss', {responseVersion: version, statusCode: 200, statusDescription: 'a promotion'}, (err: Error) => {
    if (err) {
      console.log('did not do the update');
    } else {
      console.log('The update worked!!!!');
    }
  });
}
```
