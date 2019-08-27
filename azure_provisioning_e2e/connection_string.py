# # -------------------------------------------------------------------------
# # Copyright (c) Microsoft Corporation. All rights reserved.
# # Licensed under the MIT License. See License.txt in the project root for
# # license information.
# # --------------------------------------------------------------------------
# from azure.iot.device.common.connection_string import ConnectionString
# from azure.iot.device.common.sastoken import SasToken
#
#
# def connection_string_to_sas_token(conn_str):
#     """
#     parse an IoTHub service connection string and return the host and a shared access
#     signature that can be used to connect to the given hub
#     """
#     conn_str_obj = ConnectionString(conn_str)
#     sas_token = SasToken(
#         uri=conn_str_obj.get("HostName"),
#         key=conn_str_obj.get("SharedAccessKey"),
#         key_name=conn_str_obj.get("SharedAccessKeyName"),
#     )
#
#     return {"host": conn_str_obj.get("HostName"), "sas": str(sas_token)}
