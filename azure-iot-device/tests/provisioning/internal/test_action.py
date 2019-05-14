# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import datetime
from mock import MagicMock
from azure.iot.device.provisioning.internal.action import (
    PublishAction,
    SubscribeAction,
    UnsubscribeAction,
)
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.transport.state_based_mqtt_provider import StateBasedMQTTProvider
from azure.iot.device.provisioning.sk_provisioning_device_client import (
    SymmetricKeyProvisioningDeviceClient,
)
from azure.iot.device.provisioning.provisioning_device_client_factory import (
    create_from_security_client,
)


fake_rid = "Request1234"
fake_message = "I solemnly swear that I am up to no good"
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "HighQualityFlyingBroom"
fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"


def test_initialize_of_publish_action():
    callback = MagicMock()
    topic = "$dps/registrations/PUT/iotdps-register/?$rid=" + fake_rid
    action = PublishAction(topic, fake_message, callback)

    assert action.publish_topic == topic
    assert action.message == fake_message
    assert action.callback == callback


def test_initialize_of_subscribe_action():
    callback = MagicMock()
    topic = "$dps/registrations/res/#"
    action = SubscribeAction(topic, 1, callback)

    assert action.subscribe_topic == topic
    assert action.qos == 1
    assert action.callback == callback


def test_initialize_of_unsubscribe_action():
    callback = MagicMock()
    topic = "$dps/registrations/res/#"
    action = UnsubscribeAction(topic, callback)

    assert action.unsubscribe_topic == topic
    assert action.callback == callback
