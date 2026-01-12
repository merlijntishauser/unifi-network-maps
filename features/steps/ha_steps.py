from __future__ import annotations

from behave import given, then, when


@given('a Home Assistant output directory "{path}"')
def given_ha_output_directory(_context, _path: str) -> None:
    raise AssertionError("Not implemented: HA output directory setup")


@given('Home Assistant mock data file "{path}"')
def given_ha_mock_data_file(_context, _path: str) -> None:
    raise AssertionError("Not implemented: HA mock data setup")


@when('I run the Home Assistant export with args "{args}"')
def when_run_ha_export(_context, _args: str) -> None:
    raise AssertionError("Not implemented: HA export command")


@then('the Home Assistant output contains file "{filename}"')
def then_ha_output_contains_file(_context, _filename: str) -> None:
    raise AssertionError("Not implemented: HA output file check")


@then('the Home Assistant JSON contains keys "{keys}"')
def then_ha_json_contains_keys(_context, _keys: str) -> None:
    raise AssertionError("Not implemented: HA JSON schema check")


@then('the Home Assistant JSON ports include "{keys}"')
def then_ha_json_ports_include(_context, _keys: str) -> None:
    raise AssertionError("Not implemented: HA JSON port metadata check")


@then('the Home Assistant JSON clients include "{keys}"')
def then_ha_json_clients_include(_context, _keys: str) -> None:
    raise AssertionError("Not implemented: HA JSON client metadata check")


@then('the Home Assistant JSON does not contain "{value}"')
def then_ha_json_excludes(_context, _value: str) -> None:
    raise AssertionError("Not implemented: HA JSON secret check")


@then('the Home Assistant Lovelace config contains "{content}"')
def then_ha_lovelace_contains(_context, _content: str) -> None:
    raise AssertionError("Not implemented: HA Lovelace config check")


@then('the Home Assistant SVG contains "{content}"')
def then_ha_svg_contains(_context, _content: str) -> None:
    raise AssertionError("Not implemented: HA SVG drilldown hook check")
