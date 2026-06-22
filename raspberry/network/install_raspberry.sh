#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WLAN_IFACE="${WLAN_IFACE:-wlan0}"
AP_IP="192.168.10.1/24"
SSID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_ssid"])' "$ROOT_DIR/config.json")"
PASS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_password"])' "$ROOT_DIR/config.json")"

sudo apt update -qq
sudo apt install -y -qq hostapd dnsmasq mosquitto mosquitto-clients wireshark python3-pip python3-pyqt5 python3-numpy

sudo systemctl stop hostapd dnsmasq mosquitto >/dev/null 2>&1 || true

if ! ip link show "$WLAN_IFACE" >/dev/null 2>&1; then
  echo "No existe la interfaz $WLAN_IFACE"
  exit 1
fi

sudo cp "$ROOT_DIR/network/hostapd.conf" /etc/hostapd/hostapd.conf
sudo sed -i "s/^ssid=.*/ssid=$SSID/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$PASS/" /etc/hostapd/hostapd.conf
sudo cp "$ROOT_DIR/network/dnsmasq.conf" /etc/dnsmasq.conf
sudo cp "$ROOT_DIR/network/mosquitto.conf" /etc/mosquitto/conf.d/iot.conf

sudo mkdir -p /var/log/mosquitto
sudo chown mosquitto:mosquitto /var/log/mosquitto || true

if command -v nmcli >/dev/null 2>&1; then
  sudo mkdir -p /etc/NetworkManager/conf.d
  sudo tee /etc/NetworkManager/conf.d/unmanaged-$WLAN_IFACE.conf >/dev/null <<EOF
[keyfile]
unmanaged-devices=interface-name:$WLAN_IFACE
EOF
  sudo nmcli dev disconnect "$WLAN_IFACE" >/dev/null 2>&1 || true
  sudo nmcli dev set "$WLAN_IFACE" managed no >/dev/null 2>&1 || true
  sudo systemctl restart NetworkManager >/dev/null 2>&1 || true
fi

if ! grep -q '^DAEMON_CONF="/etc/hostapd/hostapd.conf"' /etc/default/hostapd; then
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' | sudo tee -a /etc/default/hostapd >/dev/null
fi

sudo rfkill unblock wifi || true
sudo ip addr flush dev "$WLAN_IFACE" || true
sudo ip addr add "$AP_IP" dev "$WLAN_IFACE"
sudo ip link set "$WLAN_IFACE" up

sudo systemctl unmask hostapd >/dev/null 2>&1 || true
sudo systemctl enable hostapd dnsmasq mosquitto >/dev/null 2>&1
sudo systemctl restart hostapd dnsmasq mosquitto

python3 -m pip install -r "$ROOT_DIR/requirements.txt" --break-system-packages || python3 -m pip install -r "$ROOT_DIR/requirements.txt"

echo "Listo: SSID=$SSID IP=192.168.10.1 MQTT=1883"
