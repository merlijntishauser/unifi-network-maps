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

  Scenario: LLDP output includes client sections when requested
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format lldp-md --include-clients --include-ports" and output file
    Then the output file contains "### Clients"

  Scenario: Mermaid output can render left-to-right direction
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--direction LR" and output file
    Then the output file contains "graph LR"

  Scenario: Mermaid group-by-type includes subgraphs
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--group-by-type" and output file
    Then the output file contains "subgraph"

  Scenario: MkDocs compact legend uses HTML legend block
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format mkdocs --legend-style compact" and output file
    Then the output file contains "data-unifi-legend"

  Scenario: MkDocs diagram legend renders a legend section
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format mkdocs --legend-style diagram" and output file
    Then the output file contains "## Legend"

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

  Scenario: Console script entrypoint renders help
    When I run the console entrypoint with "--help"
    Then stdout contains "usage:"

  Scenario: Inventory output renders a device table
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format inventory --only-unifi" and output file
    Then the output file contains "| Name"

  Scenario: Inventory output includes clients when requested
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format inventory --include-clients --client-scope all" and output file
    Then the output file contains "| Name"

  Scenario: SVG output with isometric icon set
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format svg-iso --icon-set isometric" and output file
    Then the output file contains "<image"

  Scenario: SVG output with modern icon set
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format svg-iso --icon-set modern" and output file
    Then the output file contains "<image"

  Scenario: SVG output uses theme default icon set
    Given the mock data file "examples/mock_data.json"
    When I run the CLI with args "--format svg-iso --theme unifi" and output file
    Then the output file contains "<image"
