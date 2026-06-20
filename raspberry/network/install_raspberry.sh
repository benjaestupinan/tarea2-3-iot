#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WLAN_IFACE="${WLAN_IFACE:-wlan0}"
AP_IP="192.168.10.1/24"
SSID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_ssid"])' "$ROOT_DIR/config.json")"
PASS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_password"])' "$ROOT_DIR/config.json")"

sudo apt update
sudo apt install -y hostapd dnsmasq mosquitto wireshark python3-pip

sudo systemctl stop hostapd || true
sudo systemctl stop dnsmasq || true
sudo systemctl stop mosquitto || true

sudo cp "$ROOT_DIR/network/hostapd.conf" /etc/hostapd/hostapd.conf
sudo sed -i "s/^ssid=.*/ssid=$SSID/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$PASS/" /etc/hostapd/hostapd.conf
sudo cp "$ROOT_DIR/network/dnsmasq.conf" /etc/dnsmasq.conf
sudo cp "$ROOT_DIR/network/mosquitto.conf" /etc/mosquitto/conf.d/iot.conf

if ! grep -q '^DAEMON_CONF="/etc/hostapd/hostapd.conf"' /etc/default/hostapd; then
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' | sudo tee -a /etc/default/hostapd >/dev/null
fi

sudo ip addr flush dev "$WLAN_IFACE" || true
sudo ip addr add "$AP_IP" dev "$WLAN_IFACE"
sudo ip link set "$WLAN_IFACE" up

sudo systemctl unmask hostapd
sudo systemctl enable hostapd dnsmasq mosquitto
sudo systemctl restart hostapd dnsmasq mosquitto

python3 -m pip install -r "$ROOT_DIR/requirements.txt"

echo "AP, DHCP y Mosquitto instalados para SSID=$SSID. Captura Wireshark: tcp.port == 1883 en $WLAN_IFACE"
