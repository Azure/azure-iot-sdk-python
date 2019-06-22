# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.iothub.pipeline import pipeline_events_iothub, pipeline_ops_iothub

all_iothub_ops = [
    pipeline_ops_iothub.SetAuthProviderOperation,
    pipeline_ops_iothub.SetAuthProviderArgsOperation,
    pipeline_ops_iothub.SendD2CMessageOperation,
    pipeline_ops_iothub.SendOutputEventOperation,
]


all_iothub_events = [
    pipeline_events_iothub.C2DMessageEvent,
    pipeline_events_iothub.InputMessageEvent,
    pipeline_events_iothub.MethodRequestEvent,
]
