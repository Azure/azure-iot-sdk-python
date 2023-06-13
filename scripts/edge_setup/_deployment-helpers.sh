# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

export PATH_AGENT_PROPS=".modulesContent[\"\$edgeAgent\"][\"properties.desired\"]"
export PATH_SYSTEM_MODULES="${PATH_AGENT_PROPS}.systemModules"
export PATH_MODULES="${PATH_AGENT_PROPS}.modules"
export PATH_REGISTRY_CREDENTIALS="${PATH_AGENT_PROPS}.runtime.settings.registryCredentials"
export PATH_HUB_PROPS=".modulesContent[\"\$edgeHub\"][\"properties.desired\"]"
export PATH_ROUTES="${PATH_HUB_PROPS}.routes"
