# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import provisioningserviceclient.models
from .client import (ProvisioningServiceClient, BulkEnrollmentOperation, \
                     BulkEnrollmentOperationResult, ProvisioningServiceError, \
                     QuerySpecification, Query)

provisioningserviceclient.models._patch_models()

__all__ = [
    'ProvisioningServiceClient',
    'ProvisioningServiceError',
    'Query',
    'QuerySpecification',
    'BulkEnrollmentOperation',
    'BulkEnrollmentOperationResult',
    'models'
]
