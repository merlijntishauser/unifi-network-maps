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

# Theme variants (built-in themes)
eval $CLI --theme unifi --stdout > smoketest/themes/mermaid_unifi.mmd
eval $CLI --theme unifi-dark --stdout > smoketest/themes/mermaid_unifi_dark.mmd
eval $CLI --theme minimal --stdout > smoketest/themes/mermaid_minimal.mmd
eval $CLI --theme classic --stdout > smoketest/themes/mermaid_classic.mmd
eval $CLI --theme classic-dark --stdout > smoketest/themes/mermaid_classic_dark.mmd
eval $CLI --theme unifi --format svg --output smoketest/themes/svg_unifi.svg
eval $CLI --theme unifi-dark --format svg --output smoketest/themes/svg_unifi_dark.svg
eval $CLI --theme minimal --format svg --output smoketest/themes/svg_minimal.svg
eval $CLI --theme classic --format svg --output smoketest/themes/svg_classic.svg
eval $CLI --theme classic-dark --format svg --output smoketest/themes/svg_classic_dark.svg
eval $CLI --theme unifi --format svg-iso --output smoketest/themes/svg_iso_unifi.svg
eval $CLI --theme unifi-dark --format svg-iso --output smoketest/themes/svg_iso_unifi_dark.svg
eval $CLI --theme minimal --format svg-iso --output smoketest/themes/svg_iso_minimal.svg
eval $CLI --theme classic --format svg-iso --output smoketest/themes/svg_iso_classic.svg
eval $CLI --theme classic-dark --format svg-iso --output smoketest/themes/svg_iso_classic_dark.svg
eval $CLI --theme unifi --legend-only --stdout > smoketest/themes/legend_unifi.mmd
eval $CLI --theme unifi-dark --legend-only --stdout > smoketest/themes/legend_unifi_dark.mmd
# Dark themes with ports, wired clients, WAN info (modern icon set)
eval $CLI --theme unifi-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_unifi_dark_ports_wan_modern.svg
eval $CLI --theme unifi-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_iso_unifi_dark_ports_wan_modern.svg
eval $CLI --theme classic-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_classic_dark_ports_wan_modern.svg
eval $CLI --theme classic-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_iso_classic_dark_ports_wan_modern.svg
eval $CLI --theme minimal-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_minimal_dark_ports_wan_modern.svg
eval $CLI --theme minimal-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set modern --output smoketest/themes/svg_iso_minimal_dark_ports_wan_modern.svg
# Dark themes with ports, wired clients, WAN info (isometric icon set)
eval $CLI --theme unifi-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_unifi_dark_ports_wan_isometric.svg
eval $CLI --theme unifi-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_iso_unifi_dark_ports_wan_isometric.svg
eval $CLI --theme classic-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_classic_dark_ports_wan_isometric.svg
eval $CLI --theme classic-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_iso_classic_dark_ports_wan_isometric.svg
eval $CLI --theme minimal-dark --format svg --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_minimal_dark_ports_wan_isometric.svg
eval $CLI --theme minimal-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label Odido --wan-speed 1Gbps --icon-set isometric --output smoketest/themes/svg_iso_minimal_dark_ports_wan_isometric.svg

# WAN variants
mkdir -p smoketest/wan
eval $CLI --format svg --wan-label Odido --wan-speed 1Gbps --output smoketest/wan/network_wan.svg
eval $CLI --format svg-iso --wan-label Odido --wan-speed 1Gbps --output smoketest/wan/network_wan_iso.svg
eval $CLI --format svg-iso --wan-label Odido --wan-speed 1Gbps --wan2-label Backup --output smoketest/wan/network_wan_dual_iso.svg

# VLAN variants (requires --include-clients for active VLAN visualization)
mkdir -p smoketest/vlan
eval $CLI --include-clients --format svg --output smoketest/vlan/network_vlan.svg
eval $CLI --include-clients --format svg-iso --output smoketest/vlan/network_vlan_iso.svg
eval $CLI --include-clients --client-scope all --format svg --output smoketest/vlan/network_vlan_all_clients.svg
eval $CLI --include-clients --client-scope all --format svg-iso --output smoketest/vlan/network_vlan_all_clients_iso.svg
eval $CLI --include-clients --max-vlan-colors 3 --format svg --output smoketest/vlan/network_vlan_max3.svg
eval $CLI --include-clients --max-vlan-colors 3 --format svg-iso --output smoketest/vlan/network_vlan_max3_iso.svg
eval $CLI --include-ports --include-clients --format svg --output smoketest/vlan/network_vlan_ports.svg
eval $CLI --include-ports --include-clients --format svg-iso --output smoketest/vlan/network_vlan_ports_iso.svg
eval $CLI --include-ports --include-clients --client-scope all --format svg-iso --output smoketest/vlan/network_vlan_ports_all_iso.svg

# Inventory variants
mkdir -p smoketest/inventory
eval $CLI --format inventory --only-unifi --resolve-hostnames --include-clients --client-scope all --output smoketest/inventory/inventory.md

echo "Smoketest complete: $(find smoketest -type f | wc -l | tr -d ' ') files generated"
