# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.iothub.models import (
    ClientPropertyCollection,
    ClientProperties,
    generate_writable_property_response,
)


@pytest.mark.describe("generate_writable_property_response()")
class TestGenerateWritablePropertyResponse(object):
    @pytest.mark.it("Returns a dictionary with keys mapping to the provided values")
    def test_dictionary(self):
        value = "some_value"
        ack_code = 200
        ack_description = "Success"
        ack_version = 12
        writable_prop_response = generate_writable_property_response(
            value, ack_code, ack_description, ack_version
        )
        assert writable_prop_response["value"] == value
        assert writable_prop_response["ac"] == ack_code
        assert writable_prop_response["ad"] == ack_description
        assert writable_prop_response["av"] == ack_version


@pytest.mark.describe("ClientPropertyCollection")
class TestClientPropertyCollection(object):
    @pytest.mark.it("Instantiates with an empty backing object")
    def test_instantiation(self):
        cpc = ClientPropertyCollection()
        assert cpc.backing_object == {}

    @pytest.mark.it(
        "Maintains a '$version' property mapped to the backing object's '$version' value"
    )
    def test_version(self):
        cpc = ClientPropertyCollection()
        assert cpc.version is None
        cpc.backing_object = {"$version": 12}
        assert cpc.version == 12

    @pytest.mark.it("Can set and retrieve properties on the backing object via APIs")
    def test_set_get_property(self):
        property_name = "some_property"
        property_value = "value"
        cpc = ClientPropertyCollection()
        assert cpc.get_property(property_name) is None
        assert property_name not in cpc.backing_object.keys()

        cpc.set_property(property_name, property_value)

        assert cpc.get_property(property_name) == property_value
        assert cpc.backing_object[property_name] == property_value

    @pytest.mark.it(
        "Can return a specified default value when retrieving a property that does not exist"
    )
    def test_get_property_default(self):
        property_name = "some_property"
        property_value = "value"
        default_value = 12
        cpc = ClientPropertyCollection()
        assert cpc.get_property(property_name) is None
        assert property_name not in cpc.backing_object.keys()
        # Value doesn't exist, so returns default
        assert cpc.get_property(property_name, default=default_value) == default_value
        assert property_name not in cpc.backing_object.keys()

        cpc.set_property(property_name, property_value)
        assert cpc.get_property(property_name) == property_value
        assert cpc.backing_object[property_name] == property_value
        # Value does exist, so returns the value instead of the default
        assert cpc.get_property(property_name, default=default_value) == property_value
        assert property_value != default_value

    @pytest.mark.it("Can set and retreive component properties on the backing object via APIs")
    def test_set_get_component_property(self):
        property_name = "some_property"
        component_name = "some_component"
        property_value = "value"
        cpc = ClientPropertyCollection()
        assert cpc.get_component_property(component_name, property_name) is None
        assert component_name not in cpc.backing_object.keys()

        cpc.set_component_property(component_name, property_name, property_value)

        assert cpc.get_component_property(component_name, property_name) == property_value
        assert cpc.backing_object[component_name][property_name] == property_value

    @pytest.mark.it(
        "Can return a specified default value when retrieving a component property that does not exist"
    )
    def test_get_component_property_default(self):
        component_name = "some_component"
        property_name1 = "some_property"
        property_value1 = "value"
        property_name2 = "some_other_property"
        property_value2 = "other_value"
        default_value = 12
        cpc = ClientPropertyCollection()
        assert cpc.get_component_property(component_name, property_name1) is None
        assert component_name not in cpc.backing_object.keys()
        # Component doesn't exist, so returns default
        assert (
            cpc.get_component_property(component_name, property_name1, default=default_value)
            == default_value
        )
        assert component_name not in cpc.backing_object.keys()

        # Add a different property on the desired component, so component now exists, but target
        # property still does not
        cpc.set_component_property(component_name, property_name2, property_value2)
        assert cpc.get_component_property(component_name, property_name1) is None
        assert property_name1 not in cpc.backing_object[component_name].keys()
        assert (
            cpc.get_component_property(component_name, property_name1, default=default_value)
            == default_value
        )
        assert property_name1 not in cpc.backing_object[component_name].keys()

        # Add the target property to the desired component
        cpc.set_component_property(component_name, property_name1, property_value1)
        assert cpc.backing_object[component_name][property_name1] == property_value1

        # Value does exist, so returns the value instead of the default
        assert (
            cpc.get_component_property(component_name, property_name1, default=default_value)
            == property_value1
        )
        assert property_value1 != default_value

    @pytest.mark.it(
        "Implicitly creates a component on the backing object when setting a component property for a component that does not yet exist on the backing object"
    )
    def test_implicit_component_creation(self):
        component_name = "some_component"
        property_name = "some_property"
        property_value = "some_value"
        cpc = ClientPropertyCollection()

        # Component does not yet exist
        assert component_name not in cpc.backing_object.keys()

        # Setting the property implicitly creates the component
        cpc.set_component_property(component_name, property_name, property_value)
        assert component_name in cpc.backing_object.keys()
        # Has metadata indicating this JSON structure is a component
        assert cpc.backing_object[component_name]["__t"] == "c"
        # Value was set on the component
        assert cpc.backing_object[component_name][property_name] == property_value

    @pytest.mark.it("Can have its backing object manually set or edited")
    def test_backing_object(self):
        cpc = ClientPropertyCollection()
        assert cpc.backing_object == {}
        properties_json = {
            "property1": 12,
            "property2": 13,
            "component1": {
                "__t": "c",
                "component_property1": "foo",
                "component_property2": "bar",
            },
            "$version": 17,
        }
        # Can be manually set
        cpc.backing_object = properties_json
        assert cpc.get_property("property1") == properties_json["property1"]
        assert cpc.get_property("property2") == properties_json["property2"]
        assert (
            cpc.get_component_property("component1", "component_property1")
            == properties_json["component1"]["component_property1"]
        )
        assert (
            cpc.get_component_property("component1", "component_property2")
            == properties_json["component1"]["component_property2"]
        )
        assert cpc.version == properties_json["$version"]

        # Can have new components set
        component2_json = {
            "__t": "c",
            "component_property3": "buzz",
            "component_property4": "baz",
        }
        cpc.backing_object["component2"] = component2_json
        assert (
            cpc.get_component_property("component2", "component_property3")
            == component2_json["component_property3"]
        )
        assert (
            cpc.get_component_property("component2", "component_property4")
            == component2_json["component_property4"]
        )

        # Can have new properties and component properties set
        cpc.backing_object["property3"] = 15
        assert cpc.get_property("property3") == 15
        cpc.backing_object["component1"]["component_property5"] = "quz"
        assert cpc.get_component_property("component1", "component_property5") == "quz"

        # Can have existing properties and component properties updated
        assert cpc.backing_object["property1"] != 1800
        cpc.backing_object["property1"] = 1800
        assert cpc.get_property("property1") == 1800
        assert cpc.backing_object["component1"]["component_property1"] != "qux"
        cpc.backing_object["component1"]["component_property1"] = "qux"
        assert cpc.get_component_property("component1", "component_property1") == "qux"

        # Can have existing properties, component properties, and components themselves deleted
        assert "property1" in cpc.backing_object.keys()
        del cpc.backing_object["property1"]
        assert cpc.get_property("property1") is None
        assert "component_property1" in cpc.backing_object["component1"].keys()
        del cpc.backing_object["component1"]["component_property1"]
        assert cpc.get_component_property("component1", "component_property1") is None
        assert "component2" in cpc.backing_object.keys()
        assert "component_property3" in cpc.backing_object["component2"].keys()
        assert "component_property4" in cpc.backing_object["component2"].keys()
        del cpc.backing_object["component2"]
        assert cpc.get_component_property("component2", "component_property3") is None
        assert cpc.get_component_property("component2", "component_property4") is None


@pytest.mark.describe("ClientProperties")
class TestClientProperties(object):
    @pytest.mark.it(
        "Initializes with the writeable_properties_requests attribute set to a empty ClientPropertyCollection object"
    )
    def test_writable_properties_requests(self):
        client_properties = ClientProperties()
        assert isinstance(client_properties.writable_properties_requests, ClientPropertyCollection)
        assert client_properties.writable_properties_requests.backing_object == {}

    @pytest.mark.it(
        "Initializes with the reported_from_device attribute set to a empty ClientPropertyCollection object"
    )
    def test_reported_from_device(self):
        client_properties = ClientProperties()
        assert isinstance(client_properties.reported_from_device, ClientPropertyCollection)
        assert client_properties.reported_from_device.backing_object == {}
