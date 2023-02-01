# TESTS
## DELETE IOTHUB
Connection Refused: broker unavailable. 
['azure.iot.device.common.transport_exceptions.ConnectionFailedError: Connection Refused: broker unavailable.\n']
['azure.iot.device.common.transport_exceptions.UnauthorizedError: Connection Refused: not authorised.\n']
## UNLINK IOTHUB WITH DPS
No change if device was already connected to IoTHub
# DELETE DEVICE IDENTITY FROM IOTHUB
'Credentials invalid, could not connect'

Failed to connect the device client due to error :ConnectionFailedError.Sleeping and retrying after 10 seconds
Failed to connect the device client due to error :CredentialError.Sleeping and retrying after 81 seconds


if any thing happens while the message is travelling via netwrok stack then nothing can be done




2023-01-31 16:37:33,409 INFO  (Thread-15) mqtt_transport.py:on_disconnect():disconnected with result code: 7
2023-01-31 16:37:33,475 WARNING (callback) handle_exceptions.py:handle_background_exception():['azure.iot.device.common.transport_exceptions.ConnectionDroppedError: Unexpected disconnection\n']
2023-01-31 16:37:33,904 INFO  (pipeline) pipeline_stages_mqtt.py:_on_mqtt_connection_failure():MQTTTransportStage: _on_mqtt_connection_failure called: Connection Refused: not authorised.
2023-01-31 16:37:33,910 WARNING (callback) handle_exceptions.py:handle_background_exception():['azure.iot.device.common.transport_exceptions.UnauthorizedError: Connection Refused: not authorised.\n']
2023-01-31 16:37:34,700 INFO  (pipeline) pipeline_stages_mqtt.py:_on_mqtt_connection_failure():MQTTTransportStage: _on_mqtt_connection_failure called: Connection Refused: not authorised.