Feature: CLI validation and error handling
  Scenario: MkDocs sidebar legend requires output
    Given the mock data file "examples/mock_data.json"
    When I run the CLI expecting failure with args "--format mkdocs --mkdocs-sidebar-legend"
    Then the command fails with exit code "2"
    And stderr contains "--mkdocs-sidebar-legend requires --output"

  Scenario: MkDocs invalid timezone logs a warning
    Given the mock data file "examples/mock_data.json"
    When I run the CLI to render "mkdocs" with mkdocs timestamp zone "Invalid/Zone"
    Then stderr contains "Invalid mkdocs timestamp zone"
    And the output file does not contain "Generated:"

  Scenario: Unsupported format is rejected by argparse
    When I run the CLI expecting failure with args "--format not-a-format"
    Then the command fails with exit code "2"
    And stderr contains "invalid choice"
