Feature: CLI output variants
  Scenario: Mermaid markdown output includes a code fence
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format mermaid --markdown" and output file
    Then the output file contains "```mermaid"

  Scenario: Legend-only output renders a legend
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--legend-only" and output file
    Then the output file contains "subgraph legend"

  Scenario: LLDP output renders a table header
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format lldp-md" and output file
    Then the output file contains "# LLDP Neighbors"

  Scenario: MkDocs sidebar legend writes assets
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format mkdocs --mkdocs-sidebar-legend" and output file
    Then the mkdocs sidebar assets are written

  Scenario: Mock data generation writes JSON
    When I run the CLI to generate mock data
    Then the output file contains "devices"
    And the output file contains "clients"

  Scenario: Module entrypoint renders help
    When I run the module entrypoint with "--help"
    Then stdout contains "usage:"
