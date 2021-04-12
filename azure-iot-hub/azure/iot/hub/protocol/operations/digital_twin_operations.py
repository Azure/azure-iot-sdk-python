# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.pipeline import ClientRawResponse
from msrest.exceptions import HttpOperationError

from .. import models


class DigitalTwinOperations(object):
    """DigitalTwinOperations operations.

    :param client: Client for service requests.
    :param config: Configuration of service client.
    :param serializer: An object model serializer.
    :param deserializer: An object model deserializer.
    :ivar api_version: Version of the Api. Constant value: "2021-04-12".
    """

    models = models

    def __init__(self, client, config, serializer, deserializer):

        self._client = client
        self._serialize = serializer
        self._deserialize = deserializer

        self.config = config
        self.api_version = "2021-04-12"

    def get_digital_twin(self, id, custom_headers=None, raw=False, **operation_config):
        """Gets a digital twin.

        :param id: Digital Twin ID.
        :type id: str
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :return: object or ClientRawResponse if raw=true
        :rtype: object or ~msrest.pipeline.ClientRawResponse
        :raises:
         :class:`HttpOperationError<msrest.exceptions.HttpOperationError>`
        """
        # Construct URL
        url = self.get_digital_twin.metadata["url"]
        path_format_arguments = {"id": self._serialize.url("id", id, "str")}
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )

        # Construct headers
        header_parameters = {}
        header_parameters["Accept"] = "application/json"
        if custom_headers:
            header_parameters.update(custom_headers)

        # Construct and send request
        request = self._client.get(url, query_parameters, header_parameters)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [200]:
            raise HttpOperationError(self._deserialize, response)

        deserialized = None
        header_dict = {}

        if response.status_code == 200:
            deserialized = self._deserialize("object", response)
            header_dict = {"ETag": "str"}

        if raw:
            client_raw_response = ClientRawResponse(deserialized, response)
            client_raw_response.add_headers(header_dict)
            return client_raw_response

        return deserialized

    get_digital_twin.metadata = {"url": "/digitaltwins/{id}"}

    def update_digital_twin(
        self,
        id,
        digital_twin_patch,
        if_match=None,
        custom_headers=None,
        raw=False,
        **operation_config
    ):
        """Updates a digital twin.

        :param id: Digital Twin ID.
        :type id: str
        :param digital_twin_patch: json-patch contents to update.
        :type digital_twin_patch: list[object]
        :param if_match:
        :type if_match: str
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :return: None or ClientRawResponse if raw=true
        :rtype: None or ~msrest.pipeline.ClientRawResponse
        :raises:
         :class:`HttpOperationError<msrest.exceptions.HttpOperationError>`
        """
        # Construct URL
        url = self.update_digital_twin.metadata["url"]
        path_format_arguments = {"id": self._serialize.url("id", id, "str")}
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )

        # Construct headers
        header_parameters = {}
        header_parameters["Content-Type"] = "application/json; charset=utf-8"
        if custom_headers:
            header_parameters.update(custom_headers)
        if if_match is not None:
            header_parameters["If-Match"] = self._serialize.header("if_match", if_match, "str")

        # Construct body
        body_content = self._serialize.body(digital_twin_patch, "[object]")

        # Construct and send request
        request = self._client.patch(url, query_parameters, header_parameters, body_content)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [202]:
            raise HttpOperationError(self._deserialize, response)

        if raw:
            client_raw_response = ClientRawResponse(None, response)
            client_raw_response.add_headers({"ETag": "str", "Location": "str"})
            return client_raw_response

    update_digital_twin.metadata = {"url": "/digitaltwins/{id}"}

    def invoke_root_level_command(
        self,
        id,
        command_name,
        payload,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
        custom_headers=None,
        raw=False,
        **operation_config
    ):
        """Invoke a digital twin root level command.

        Invoke a digital twin root level command.

        :param id:
        :type id: str
        :param command_name:
        :type command_name: str
        :param payload:
        :type payload: object
        :param connect_timeout_in_seconds: Maximum interval of time, in
         seconds, that the digital twin command will wait for the answer.
        :type connect_timeout_in_seconds: int
        :param response_timeout_in_seconds: Maximum interval of time, in
         seconds, that the digital twin command will wait for the answer.
        :type response_timeout_in_seconds: int
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :return: object or ClientRawResponse if raw=true
        :rtype: object or ~msrest.pipeline.ClientRawResponse
        :raises:
         :class:`HttpOperationError<msrest.exceptions.HttpOperationError>`
        """
        # Construct URL
        url = self.invoke_root_level_command.metadata["url"]
        path_format_arguments = {
            "id": self._serialize.url("id", id, "str"),
            "commandName": self._serialize.url("command_name", command_name, "str"),
        }
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )
        if connect_timeout_in_seconds is not None:
            query_parameters["connectTimeoutInSeconds"] = self._serialize.query(
                "connect_timeout_in_seconds", connect_timeout_in_seconds, "int"
            )
        if response_timeout_in_seconds is not None:
            query_parameters["responseTimeoutInSeconds"] = self._serialize.query(
                "response_timeout_in_seconds", response_timeout_in_seconds, "int"
            )

        # Construct headers
        header_parameters = {}
        header_parameters["Accept"] = "application/json"
        header_parameters["Content-Type"] = "application/json; charset=utf-8"
        if custom_headers:
            header_parameters.update(custom_headers)

        # Construct body
        body_content = self._serialize.body(payload, "object")

        # Construct and send request
        request = self._client.post(url, query_parameters, header_parameters, body_content)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [200]:
            raise HttpOperationError(self._deserialize, response)

        deserialized = None
        header_dict = {}

        if response.status_code == 200:
            deserialized = self._deserialize("object", response)
            header_dict = {"x-ms-command-statuscode": "int", "x-ms-request-id": "str"}

        if raw:
            client_raw_response = ClientRawResponse(deserialized, response)
            client_raw_response.add_headers(header_dict)
            return client_raw_response

        return deserialized

    invoke_root_level_command.metadata = {"url": "/digitaltwins/{id}/commands/{commandName}"}

    def invoke_component_command(
        self,
        id,
        component_path,
        command_name,
        payload,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
        custom_headers=None,
        raw=False,
        **operation_config
    ):
        """Invoke a digital twin command.

        Invoke a digital twin command.

        :param id:
        :type id: str
        :param component_path:
        :type component_path: str
        :param command_name:
        :type command_name: str
        :param payload:
        :type payload: object
        :param connect_timeout_in_seconds: Maximum interval of time, in
         seconds, that the digital twin command will wait for the answer.
        :type connect_timeout_in_seconds: int
        :param response_timeout_in_seconds: Maximum interval of time, in
         seconds, that the digital twin command will wait for the answer.
        :type response_timeout_in_seconds: int
        :param dict custom_headers: headers that will be added to the request
        :param bool raw: returns the direct response alongside the
         deserialized response
        :param operation_config: :ref:`Operation configuration
         overrides<msrest:optionsforoperations>`.
        :return: object or ClientRawResponse if raw=true
        :rtype: object or ~msrest.pipeline.ClientRawResponse
        :raises:
         :class:`HttpOperationError<msrest.exceptions.HttpOperationError>`
        """
        # Construct URL
        url = self.invoke_component_command.metadata["url"]
        path_format_arguments = {
            "id": self._serialize.url("id", id, "str"),
            "componentPath": self._serialize.url("component_path", component_path, "str"),
            "commandName": self._serialize.url("command_name", command_name, "str"),
        }
        url = self._client.format_url(url, **path_format_arguments)

        # Construct parameters
        query_parameters = {}
        query_parameters["api-version"] = self._serialize.query(
            "self.api_version", self.api_version, "str"
        )
        if connect_timeout_in_seconds is not None:
            query_parameters["connectTimeoutInSeconds"] = self._serialize.query(
                "connect_timeout_in_seconds", connect_timeout_in_seconds, "int"
            )
        if response_timeout_in_seconds is not None:
            query_parameters["responseTimeoutInSeconds"] = self._serialize.query(
                "response_timeout_in_seconds", response_timeout_in_seconds, "int"
            )

        # Construct headers
        header_parameters = {}
        header_parameters["Accept"] = "application/json"
        header_parameters["Content-Type"] = "application/json; charset=utf-8"
        if custom_headers:
            header_parameters.update(custom_headers)

        # Construct body
        body_content = self._serialize.body(payload, "object")

        # Construct and send request
        request = self._client.post(url, query_parameters, header_parameters, body_content)
        response = self._client.send(request, stream=False, **operation_config)

        if response.status_code not in [200]:
            raise HttpOperationError(self._deserialize, response)

        deserialized = None
        header_dict = {}

        if response.status_code == 200:
            deserialized = self._deserialize("object", response)
            header_dict = {"x-ms-command-statuscode": "int", "x-ms-request-id": "str"}

        if raw:
            client_raw_response = ClientRawResponse(deserialized, response)
            client_raw_response.add_headers(header_dict)
            return client_raw_response

        return deserialized

    invoke_component_command.metadata = {
        "url": "/digitaltwins/{id}/components/{componentPath}/commands/{commandName}"
    }
