Feature: Home Assistant integration POC
  Scenario: HA export writes SVG + JSON assets
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant output contains file "network.svg"
    And the Home Assistant output contains file "network.json"

  Scenario: HA JSON schema contains devices, ports, links
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant JSON contains keys "devices,ports,links"

  Scenario: HA JSON includes per-port PoE metadata
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant JSON ports include "poe_status,poe_power_w"

  Scenario: HA JSON includes client drilldown fields
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant JSON clients include "name,mac,connected_port"

  Scenario: HA export avoids secrets
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant JSON does not contain "UNIFI_PASS"

  Scenario: HA export writes Lovelace card config
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant output contains file "lovelace.yaml"
    And the Home Assistant Lovelace config contains "type: custom:unifi-network-map"

  Scenario: HA SVG includes drilldown data attributes
    Given a Home Assistant output directory "smoketest/ha"
    And Home Assistant mock data file "examples/mock_data.json"
    When I run the Home Assistant export with args "--ha-output smoketest/ha"
    Then the Home Assistant SVG contains "data-device-id"
    And the Home Assistant SVG contains "data-port-id"
