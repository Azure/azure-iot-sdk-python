# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module contains constants related to the pipeline package.
"""

REGISTER = "register"
QUERY = "query"

"""
Default interval for polling, to use in case service doesn't provide it to us.
"""
DEFAULT_POLLING_INTERVAL = 2

"""
Default timeout to use when communicating with the service
"""

DEFAULT_TIMEOUT_INTERVAL = 30

SUBSCRIBE_TOPIC_PROVISIONING = "$dps/registrations/res/#"
"""
The first part of the topic string used for publishing.
The registration request id (rid) value is appended to this.
"""
PUBLISH_TOPIC_REGISTRATION = "$dps/registrations/PUT/iotdps-register/?$rid={}"
"""
The topic string used for publishing a query request.
This must be provided with the registration request id (rid) as well as the operation id
"""
PUBLISH_TOPIC_QUERYING = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid={}&operationId={}"
