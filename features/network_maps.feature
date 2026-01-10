Feature: Render outputs from mock data
  Scenario: Mermaid output includes a graph
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mermaid" with ports
    Then the output file contains "graph"

  Scenario: SVG ISO output is generated
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "svg-iso" with clients
    Then the output file starts with "<svg"

  Scenario: Mermaid output with clients includes a graph
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mermaid" with clients
    Then the output file contains "graph"

  Scenario: SVG output with ports is generated
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "svg" with ports
    Then the output file starts with "<svg"

  Scenario: SVG ISO output with ports and clients is generated
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "svg-iso" with ports and clients
    Then the output file starts with "<svg"

  Scenario: MkDocs output includes a map section
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mkdocs" with defaults
    Then the output file contains "## Map"

  Scenario: MkDocs output renders dual theme blocks
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mkdocs" with mkdocs dual theme
    Then the output file contains "unifi-mermaid--dark"

  Scenario: MkDocs output can skip timestamps
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mkdocs" with mkdocs timestamp off
    Then the output file does not contain "Generated:"
