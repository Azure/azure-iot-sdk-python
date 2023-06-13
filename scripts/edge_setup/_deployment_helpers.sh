# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

PATH_AGENT_PROPS=".modulesContent[\"\$edgeAgent\"][\"properties.desired\"]"
PATH_SYSTEM_MODULES="${PATH_AGENT_PROPS}.systemModules"
PATH_MODULES="${PATH_AGENT_PROPS}.modules"
PATH_REGISTRY_CREDENTIALS="${PATH_AGENT_PROPS}.runtime.settings.registryCredentials"
PATH_HUB_PROPS=".modulesContent[\"\$edgeHub\"][\"properties.desired\"]"
PATH_ROUTES="${PATH_HUB_PROPS}.routes"
