# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class PipelineNucleus(object):
    """Contains data and information shared across the pipeline"""

    def __init__(self, pipeline_configuration):
        self.pipeline_configuration = pipeline_configuration
        self.connected = False
