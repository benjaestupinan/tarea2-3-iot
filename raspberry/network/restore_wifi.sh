#!/usr/bin/env bash
set -euo pipefail

WLAN_IFACE="${WLAN_IFACE:-wlan0}"

sudo systemctl stop hostapd dnsmasq mosquitto >/dev/null 2>&1 || true
sudo ip addr flush dev "$WLAN_IFACE" || true

if command -v nmcli >/dev/null 2>&1; then
  sudo rm -f "/etc/NetworkManager/conf.d/unmanaged-$WLAN_IFACE.conf"
  sudo nmcli dev set "$WLAN_IFACE" managed yes >/dev/null 2>&1 || true
  sudo systemctl restart NetworkManager >/dev/null 2>&1 || true
  sudo nmcli radio wifi on >/dev/null 2>&1 || true
fi

sudo ip link set "$WLAN_IFACE" up || true

echo "WiFi restaurado en $WLAN_IFACE. Reconectate desde la interfaz grafica o con nmcli."
