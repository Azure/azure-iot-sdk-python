# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from service import VERSION
from models import IndividualEnrollment, EnrollmentGroup, DeviceRegistrationState
from serviceclient.service.operations import DeviceEnrollmentOperations


class Query(object):
    """
    Query object that can be used to iterate over Provisioning Service data
    corresponding to a given QuerySpecification.

    Note that for general usage, Query objects should be generated using a
    ProvisioningServiceClient instance, not directly constructed.

    Data Attributes:
    page_size (int): Max number of results returned per page
    has_next (bool): Indicates if the Query has more results to return
    continuation_token (str): Token indicating current position in list of results
    """

    page_size_header = "x-ms-max-item-count"
    continuation_token_header = "x-ms-continuation"
    item_type_header = "x-ms-item-type"
    authorization_header = "Authorization"

    def __init__(self, query_spec, query_fn, sastoken_factory, api_version, page_size=None):
        """
        Constructor for internal use only

        Parameters:
        query_spec (QuerySpecification): The specification of the desired query
        query_fn (function/method): A function/method to make a query to the
            Provisioning Service. Note well that query_fn must take args in the format
            query_fn(qs: QuerySpecification, api_version: str, cust_headers: dict, raw_resp: bool)
            and return a ClientRawResponse when raw_resp == True
        sastoken_factory (SasTokenFactory): A factory that generates SasToken objects
        page_size (int)[optional]: Max results per page
        api_version (str): version of the Provisioning Service API to use
        """
        self._query_spec = query_spec
        self._query_fn = query_fn
        self.page_size = page_size
        self._api_version = api_version
        self._sastoken_factory = sastoken_factory
        self.has_next = True
        self.continuation_token = None

    def __iter__(self):
        self.continuation_token = None
        return self

    def __next__(self):
        return self.next()

    @property
    def page_size(self):
        return self.__page_size

    @page_size.setter
    def page_size(self, value):
        if value is None or value > 0:
            self.__page_size = value
        else:
            raise ValueError("Page size must be a positive number")

    def next(self, continuation_token=None):
        """
        Get the next page of results

        Parameters:
        continuation_token (str)[optional]: Token indicating a specific point in
            the results to start from

        Returns:
        List containing the next page of results.
        """
        if not self.has_next:
            raise StopIteration("No more results")

        if not continuation_token:
            continuation_token = self.continuation_token

        if self.page_size is not None:
            page_size = str(self.__page_size)
        else:
            page_size = self.__page_size

        custom_headers = {}
        custom_headers[Query.authorization_header] = str(self._sastoken_factory.generate_sastoken())
        custom_headers[Query.continuation_token_header] = continuation_token
        custom_headers[Query.page_size_header] = page_size

        raw_resp = self._query_fn(self._query_spec, self._api_version, custom_headers, True)
        if not raw_resp.output:
            raise StopIteration("No more results")

        self.continuation_token = raw_resp.headers[Query.continuation_token_header]
        self.has_next = self.continuation_token != None

        return raw_resp.output
