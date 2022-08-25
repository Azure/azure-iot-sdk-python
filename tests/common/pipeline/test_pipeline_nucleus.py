# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.common.pipeline.pipeline_nucleus import PipelineNucleus, ConnectionState


logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("PipelineNucleus - Instantiation")
class TestPipelineNucleusInstantiation(object):
    @pytest.fixture
    def pipeline_config(self, mocker):
        return mocker.MagicMock()

    @pytest.mark.it(
        "Instantiates with the 'pipeline_configuration' attribute set the the value of the provided 'pipeline_configuration' parameter"
    )
    def test_pipeline_config(self, pipeline_config):
        nucleus = PipelineNucleus(pipeline_configuration=pipeline_config)
        assert nucleus.pipeline_configuration is pipeline_config

    @pytest.mark.it("Instantiates with the 'connection_state' attribute set to DISCONNECTED")
    def test_connected(self, pipeline_config):
        nucleus = PipelineNucleus(pipeline_config)
        assert nucleus.connection_state is ConnectionState.DISCONNECTED


@pytest.mark.describe("PipelineNucleus - PROPERTY .connected")
class TestPipelineNucleusPROPERTYConnected(object):
    @pytest.fixture
    def nucleus(self, mocker):
        pl_cfg = mocker.MagicMock()
        return PipelineNucleus(pl_cfg)

    @pytest.mark.it("Is a read-only property")
    def test_read_only(self, nucleus):
        with pytest.raises(AttributeError):
            nucleus.connected = False

    @pytest.mark.it("Returns True if the '.connection_state' attribute is CONNECTED")
    def test_connected(self, nucleus):
        nucleus.connection_state = ConnectionState.CONNECTED
        assert nucleus.connected

    @pytest.mark.it("Returns False if the '.connection_state' attribute has any other value")
    @pytest.mark.parametrize(
        "state",
        [
            ConnectionState.DISCONNECTED,
            ConnectionState.CONNECTING,
            ConnectionState.DISCONNECTING,
            ConnectionState.REAUTHORIZING,
        ],
    )
    def test_not_connected(self, nucleus, state):
        nucleus.connection_state = state
        assert not nucleus.connected
