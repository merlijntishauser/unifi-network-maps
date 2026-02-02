#!/usr/bin/env bash
# Smoketest runner - generates all output variants for live UniFi
set -e

CLI="PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli"

rm -rf smoketest
mkdir -p smoketest/{json,lldp,mermaid,mkdocs,svg,svg-iso,themes}

# Mermaid variants
eval $CLI --stdout > smoketest/mermaid/network.mmd
eval $CLI --markdown --output smoketest/mermaid/network.md
eval $CLI --group-by-type --stdout > smoketest/mermaid/network_grouped.mmd
eval $CLI --include-ports --include-clients --stdout > smoketest/mermaid/network_ports_clients.mmd
eval $CLI --include-clients --client-scope wireless --stdout > smoketest/mermaid/network_clients_wireless.mmd
eval $CLI --include-clients --client-scope all --stdout > smoketest/mermaid/network_clients_all.mmd
eval $CLI --include-clients --only-unifi --stdout > smoketest/mermaid/network_clients_only_unifi.mmd
eval $CLI --include-ports --stdout > smoketest/mermaid/network_ports.mmd
eval $CLI --legend-only --stdout > smoketest/mermaid/legend.mmd

# MkDocs variants
eval $CLI --format mkdocs --output smoketest/mkdocs/unifi-network.md
eval $CLI --format mkdocs --include-clients --output smoketest/mkdocs/unifi-network-clients.md
eval $CLI --format mkdocs --legend-scale 0.6 --output smoketest/mkdocs/unifi-network-legend-scaled.md
eval $CLI --format mkdocs --legend-style diagram --output smoketest/mkdocs/unifi-network-legend-diagram.md
eval $CLI --format mkdocs --mkdocs-sidebar-legend --output smoketest/mkdocs/unifi-network-sidebar-legend.md
eval $CLI --format mkdocs --include-clients --mkdocs-dual-theme --mkdocs-sidebar-legend --output smoketest/mkdocs/unifi-network-dual-theme-and-clients.md

# LLDP markdown variants
eval $CLI --format lldp-md --output smoketest/lldp/lldp.md
eval $CLI --format lldp-md --include-clients --output smoketest/lldp/lldp_clients.md
eval $CLI --format lldp-md --include-clients --client-scope wireless --output smoketest/lldp/lldp_clients_wireless.md
eval $CLI --format lldp-md --include-clients --client-scope all --output smoketest/lldp/lldp_clients_all.md

# SVG variants
eval $CLI --format svg --output smoketest/svg/network.svg
eval $CLI --format svg-iso --output smoketest/svg-iso/network_iso.svg
eval $CLI --include-clients --format svg --output smoketest/svg/network_clients.svg
eval $CLI --include-clients --format svg-iso --output smoketest/svg-iso/network_clients_iso.svg
eval $CLI --include-clients --only-unifi --format svg --output smoketest/svg/network_clients_only_unifi.svg
eval $CLI --include-clients --only-unifi --format svg-iso --output smoketest/svg-iso/network_clients_only_unifi_iso.svg
eval $CLI --include-clients --client-scope wireless --format svg --output smoketest/svg/network_clients_wireless.svg
eval $CLI --include-clients --client-scope wireless --format svg-iso --output smoketest/svg-iso/network_clients_wireless_iso.svg
eval $CLI --include-clients --client-scope all --format svg --output smoketest/svg/network_clients_all.svg
eval $CLI --include-clients --client-scope all --format svg-iso --output smoketest/svg-iso/network_clients_all_iso.svg
eval $CLI --include-ports --format svg --output smoketest/svg/network_ports.svg
eval $CLI --include-ports --format svg-iso --output smoketest/svg-iso/network_ports_iso.svg
eval $CLI --include-ports --include-clients --format svg --output smoketest/svg/network_ports_clients.svg
eval $CLI --include-ports --include-clients --format svg-iso --output smoketest/svg-iso/network_ports_clients_iso.svg
eval $CLI --include-ports --include-clients --client-scope all --format svg-iso --output smoketest/svg-iso/network_ports_clients_all_iso.svg
eval $CLI --format svg --svg-layout-mode grouped --output smoketest/svg/network_grouped.svg
eval $CLI --format svg-iso --svg-layout-mode grouped --output smoketest/svg-iso/network_grouped_iso.svg
eval $CLI --include-clients --format svg --svg-layout-mode grouped --output smoketest/svg/network_clients_grouped.svg
eval $CLI --include-clients --format svg-iso --svg-layout-mode grouped --output smoketest/svg-iso/network_clients_grouped_iso.svg

# JSON
eval $CLI --format json --output smoketest/json/payload.json
eval $CLI --format json --include-clients --output smoketest/json/payload_clients.json

# Theme variants
eval $CLI --theme-file src/unifi_network_maps/assets/themes/default.yaml --stdout > smoketest/themes/mermaid_default.mmd
eval $CLI --theme-file src/unifi_network_maps/assets/themes/dark.yaml --stdout > smoketest/themes/mermaid_dark.mmd
eval $CLI --theme-file src/unifi_network_maps/assets/themes/default.yaml --legend-only --stdout > smoketest/themes/legend_default.mmd
eval $CLI --theme-file src/unifi_network_maps/assets/themes/dark.yaml --legend-only --stdout > smoketest/themes/legend_dark.mmd
eval $CLI --theme-file src/unifi_network_maps/assets/themes/default.yaml --format svg --output smoketest/themes/svg_default.svg
eval $CLI --theme-file src/unifi_network_maps/assets/themes/dark.yaml --format svg --output smoketest/themes/svg_dark.svg
eval $CLI --theme-file src/unifi_network_maps/assets/themes/default.yaml --format svg-iso --output smoketest/themes/svg_iso_default.svg
eval $CLI --theme-file src/unifi_network_maps/assets/themes/dark.yaml --format svg-iso --output smoketest/themes/svg_iso_dark.svg

echo "Smoketest complete: $(find smoketest -type f | wc -l | tr -d ' ') files generated"
