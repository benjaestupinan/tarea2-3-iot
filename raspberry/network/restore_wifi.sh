#!/usr/bin/env bash
set -euo pipefail

WLAN_IFACE="${WLAN_IFACE:-wlan0}"
AP_IFACE="${AP_IFACE:-uap0}"

sudo systemctl stop hostapd dnsmasq mosquitto >/dev/null 2>&1 || true
sudo systemctl disable hostapd dnsmasq mosquitto >/dev/null 2>&1 || true
sudo systemctl kill hostapd dnsmasq >/dev/null 2>&1 || true
sudo pkill -x hostapd >/dev/null 2>&1 || true
sudo ip addr flush dev "$AP_IFACE" || true
sudo ip link set "$AP_IFACE" down >/dev/null 2>&1 || true
sudo iw dev "$AP_IFACE" del >/dev/null 2>&1 || true
sudo rfkill unblock wifi || true

if command -v nmcli >/dev/null 2>&1; then
  sudo rm -f "/etc/NetworkManager/conf.d/unmanaged-$AP_IFACE.conf"
  sudo nmcli general reload >/dev/null 2>&1 || true
  sudo nmcli dev set "$WLAN_IFACE" managed yes >/dev/null 2>&1 || true
  sudo nmcli radio wifi on >/dev/null 2>&1 || true
  sleep 3
  sudo nmcli dev wifi rescan ifname "$WLAN_IFACE" >/dev/null 2>&1 || true
  sudo nmcli dev connect "$WLAN_IFACE" >/dev/null 2>&1 || true

  active_wifi="$(nmcli -t -f DEVICE,TYPE,STATE dev status | grep "^$WLAN_IFACE:wifi:connected$" || true)"
  if [[ -z "$active_wifi" ]]; then
    profile="$(nmcli -t -f NAME,TYPE,AUTOCONNECT connection show | awk -F: '$2 == "802-11-wireless" && $3 == "yes" { print $1; exit }')"
    if [[ -n "$profile" ]]; then
      sudo nmcli connection up "$profile" ifname "$WLAN_IFACE" >/dev/null 2>&1 || true
    fi
  fi
else
  sudo systemctl restart wpa_supplicant >/dev/null 2>&1 || true
fi

sudo ip link set "$WLAN_IFACE" up || true

echo "WiFi restaurado en $WLAN_IFACE. Estado actual:"
ip -4 addr show dev "$WLAN_IFACE" || true
if command -v nmcli >/dev/null 2>&1; then
  nmcli dev status || true
fi
