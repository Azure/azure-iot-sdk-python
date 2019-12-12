# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.iothub.pipeline import http_path_iothub

logging.basicConfig(level=logging.DEBUG)

# NOTE: All tests are parametrized with multiple values for URL encoding. This is to show that the
# URL encoding is done correctly - not all URL encoding encodes the '+' character. Thus we must
# make sure any URL encoded value can encode a '+' specifically, in addition to regular encoding.


@pytest.mark.describe(".get_method_invoke_path()")
class TestGetMethodInvokePath(object):
    @pytest.mark.it("Returns the method invoke HTTP path")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_path",
        [
            pytest.param(
                "my_device",
                None,
                "twins/my_device/methods",
                id="'my_device' ==> 'twins/my_device/methods'",
            ),
            pytest.param(
                "my/device",
                None,
                "twins/my%2Fdevice/methods",
                id="'my/device' ==> 'twins/my%2Fdevice/methods'",
            ),
            pytest.param(
                "my+device",
                None,
                "twins/my%2Bdevice/methods",
                id="'my+device' ==> 'twins/my%2Bdevice/methods'",
            ),
            pytest.param(
                "my_device",
                "my_module",
                "twins/my_device/modules/my_module/methods",
                id="('my_device', 'my_module') ==> 'twins/my_device/modules/my_module/methods'",
            ),
            pytest.param(
                "my/device",
                "my?module",
                "twins/my%2Fdevice/modules/my%3Fmodule/methods",
                id="('my/device', 'my?module') ==> 'twins/my%2Fdevice/modules/my%3Fmodule/methods'",
            ),
            pytest.param(
                "my+device",
                "my+module",
                "twins/my%2Bdevice/modules/my%2Bmodule/methods",
                id="('my+device', 'my+module') ==> 'twins/my%2Bdevice/modules/my%2Bmodule/methods'",
            ),
        ],
    )
    def test_path(self, device_id, module_id, expected_path):
        path = http_path_iothub.get_method_invoke_path(device_id=device_id, module_id=module_id)
        assert path == expected_path


@pytest.mark.describe(".get_storage_info_path()")
class TestGetStorageInfoPath(object):
    @pytest.mark.it("Returns the storage info HTTP path")
    @pytest.mark.parametrize(
        "device_id, expected_path",
        [
            pytest.param("my_device", "my_device/files", id="'my_device' ==> 'my_device/files'"),
            pytest.param(
                "my/device", "my%2Fdevice/files", id="'my/device' ==> 'my%2Fdevice/files'"
            ),
            pytest.param(
                "my+device", "my%2Bdevice/files", id="'my+device' ==> 'my%2Bdevice/files'"
            ),
        ],
    )
    def test_path(self, device_id, expected_path):
        path = http_path_iothub.get_storage_info_path(device_id)
        assert path == expected_path


@pytest.mark.describe(".get_notify_blob_upload_status_path()")
class TestGetNotifyBlobUploadStatusPath(object):
    @pytest.mark.it("Returns the notify blob upload status HTTP path")
    @pytest.mark.parametrize(
        "device_id, expected_path",
        [
            pytest.param(
                "my_device",
                "my_device/files/notifications",
                id="'my_device' ==> 'my_device/files/notifications'",
            ),
            pytest.param(
                "my/device",
                "my%2Fdevice/files/notifications",
                id="'my/device' ==> 'my%2Fdevice/files/notifications'",
            ),
            pytest.param(
                "my+device",
                "my%2Bdevice/files/notifications",
                id="'my+device' ==> 'my%2Bdevice/files/notifications'",
            ),
        ],
    )
    def test_path(self, device_id, expected_path):
        path = http_path_iothub.get_notify_blob_upload_status_path(device_id)
        assert path == expected_path
