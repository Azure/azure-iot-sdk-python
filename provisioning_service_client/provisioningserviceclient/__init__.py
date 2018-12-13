# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import provisioningserviceclient.models
from .client import *

provisioningserviceclient.models._patch_models()

__all__ = [
    'ProvisioningServiceClient',
    'ProvisioningServiceError',
    'Query',
    'QuerySpecification',
    'BulkEnrollmentOperation',
    'BulkEnrollmentOperationResult',
    'models',
    'BULKOP_CREATE',
    'BULKOP_UPDATE',
    'BULKOP_DELETE',
    'BULKOP_UPDATE_IF_MATCH_ETAG'
]
