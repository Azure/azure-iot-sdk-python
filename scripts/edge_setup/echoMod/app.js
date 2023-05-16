// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.
"use strict";

const Protocol = require("azure-iot-device-mqtt").Mqtt;
const ModuleClient = require("azure-iot-device").ModuleClient;
const Message = require("azure-iot-device").Message;

ModuleClient.fromEnvironment(Protocol, (err, client) => {
  if (err) {
    console.error(`Could not create client: {err}`);
    process.exit(-1);
  } else {
    console.log("got client");

    client.on("error", (err) => {
      console.error(err.message);
    });

    client.open((err) => {
      if (err) {
        console.error(`Could not connect: {err}`);
        process.exit(-1);
      } else {
        console.log("Client connected");

        // Act on input messages to the module.
        client.on("inputMessage", (inputName, msg) => {
          if (inputName === "input1") {
            client.sendOutputEvent("output2", msg, (err) => {
              if (err) {
                console.log(`sendOutputEvent failed {err}`);
              }
            });
          } else {
            console.log(`unexpected input: {inputName}`);
          }
        });
      }
    });
  }
});
