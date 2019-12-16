def translate_error(sc, reason):
    """
    Codes_SRS_NODE_IOTHUB_REST_API_CLIENT_16_012: [Any error object returned by translate_error shall inherit from the generic Error Javascript object and have 3 properties:
    - response shall contain the IncomingMessage object returned by the HTTP layer.
    - reponseBody shall contain the content of the HTTP response.
    - message shall contain a human-readable error message.]
    """
    message = "Error: {}".format(reason)
    if sc == 400:
        # translate_error shall return an ArgumentError if the HTTP response status code is 400.
        error = "ArgumentError({})".format(message)

    elif sc == 401:
        # translate_error shall return an UnauthorizedError if the HTTP response status code is 401.
        error = "UnauthorizedError({})".format(message)

    elif sc == 403:
        # translate_error shall return an TooManyDevicesError if the HTTP response status code is 403.
        error = "TooManyDevicesError({})".format(message)

    elif sc == 404:
        if reason == "Device Not Found":
            # translate_error shall return an DeviceNotFoundError if the HTTP response status code is 404 and if the error code within the body of the error response is DeviceNotFound.
            error = "DeviceNotFoundError({})".format(message)
        elif reason == "IoTHub Not Found":
            # translate_error shall return an IotHubNotFoundError if the HTTP response status code is 404 and if the error code within the body of the error response is IotHubNotFound.
            error = "IotHubNotFoundError({})".format(message)
        else:
            error = "Error('Not found')"

    elif sc == 408:
        # translate_error shall return a DeviceTimeoutError if the HTTP response status code is 408.
        error = "DeviceTimeoutError({})".format(message)

    elif sc == 409:
        # translate_error shall return an DeviceAlreadyExistsError if the HTTP response status code is 409.
        error = "DeviceAlreadyExistsError({})".format(message)

    elif sc == 412:
        # translate_error shall return an InvalidEtagError if the HTTP response status code is 412.
        error = "InvalidEtagError({})".format(message)

    elif sc == 429:
        # translate_error shall return an ThrottlingError if the HTTP response status code is 429.]
        error = "ThrottlingError({})".format(message)

    elif sc == 500:
        # translate_error shall return an InternalServerError if the HTTP response status code is 500.
        error = "InternalServerError({})".format(message)

    elif sc == 502:
        # translate_error shall return a BadDeviceResponseError if the HTTP response status code is 502.
        error = "BadDeviceResponseError({})".format(message)

    elif sc == 503:
        # translate_error shall return an ServiceUnavailableError if the HTTP response status code is 503.
        error = "ServiceUnavailableError({})".format(message)

    elif sc == 504:
        # translate_error shall return a GatewayTimeoutError if the HTTP response status code is 504.
        error = "GatewayTimeoutError({})".format(message)

    else:
        # If the HTTP error code is unknown, translate_error should return a generic Javascript Error object.
        error = "Error({})".format(message)

    return error
