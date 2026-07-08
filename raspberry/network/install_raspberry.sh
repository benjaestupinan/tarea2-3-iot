#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WLAN_IFACE="${WLAN_IFACE:-wlan0}"
AP_IFACE="${AP_IFACE:-uap0}"
AP_IP="192.168.10.1/24"
AP_CHANNEL="${AP_CHANNEL:-$(nmcli -t -f ACTIVE,CHAN dev wifi list ifname "$WLAN_IFACE" 2>/dev/null | awk -F: '$1 == "yes" { print $2; exit }')}"
AP_CHANNEL="${AP_CHANNEL:-6}"
SSID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_ssid"])' "$ROOT_DIR/config.json")"
PASS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_password"])' "$ROOT_DIR/config.json")"
PACKAGES=(hostapd dnsmasq iw mosquitto mosquitto-clients wireshark python3-pip python3-pyqt5 python3-numpy)

missing_packages=()
for package in "${PACKAGES[@]}"; do
  if ! dpkg -s "$package" >/dev/null 2>&1; then
    missing_packages+=("$package")
  fi
done

if ((${#missing_packages[@]} > 0)); then
  sudo apt update -qq
  sudo apt install -y -qq "${missing_packages[@]}"
fi

sudo systemctl stop hostapd dnsmasq mosquitto >/dev/null 2>&1 || true

if ! ip link show "$WLAN_IFACE" >/dev/null 2>&1; then
  echo "No existe la interfaz $WLAN_IFACE"
  exit 1
fi

if ! ip link show "$AP_IFACE" >/dev/null 2>&1; then
  sudo iw dev "$WLAN_IFACE" interface add "$AP_IFACE" type __ap || sudo iw dev "$WLAN_IFACE" interface add "$AP_IFACE" type managed
fi

sudo cp "$ROOT_DIR/network/hostapd.conf" /etc/hostapd/hostapd.conf
sudo sed -i "s/^interface=.*/interface=$AP_IFACE/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^ssid=.*/ssid=$SSID/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$PASS/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^channel=.*/channel=$AP_CHANNEL/" /etc/hostapd/hostapd.conf
sudo cp "$ROOT_DIR/network/dnsmasq.conf" /etc/dnsmasq.conf
sudo sed -i "s/^interface=.*/interface=$AP_IFACE/" /etc/dnsmasq.conf
sudo cp "$ROOT_DIR/network/mosquitto.conf" /etc/mosquitto/conf.d/iot.conf

sudo mkdir -p /var/log/mosquitto
sudo touch /var/log/mosquitto/mosquitto.log
sudo chown mosquitto:mosquitto /var/log/mosquitto || true
sudo chown mosquitto:mosquitto /var/log/mosquitto/mosquitto.log || true

if command -v nmcli >/dev/null 2>&1; then
  sudo mkdir -p /etc/NetworkManager/conf.d
  sudo tee /etc/NetworkManager/conf.d/unmanaged-$AP_IFACE.conf >/dev/null <<EOF
[keyfile]
unmanaged-devices=interface-name:$AP_IFACE
EOF
  sudo nmcli dev set "$AP_IFACE" managed no >/dev/null 2>&1 || true
  sudo systemctl restart NetworkManager >/dev/null 2>&1 || true
  sleep 2
fi

if ! grep -q '^DAEMON_CONF="/etc/hostapd/hostapd.conf"' /etc/default/hostapd; then
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' | sudo tee -a /etc/default/hostapd >/dev/null
fi

sudo rfkill unblock wifi || true
sudo iw reg set CL >/dev/null 2>&1 || true
sudo ip link set "$AP_IFACE" down || true
sudo ip addr flush dev "$AP_IFACE" || true
sudo ip addr add "$AP_IP" dev "$AP_IFACE"
sudo ip link set "$AP_IFACE" up

sudo systemctl unmask hostapd >/dev/null 2>&1 || true
sudo systemctl enable hostapd dnsmasq mosquitto >/dev/null 2>&1 || true
sudo systemctl reset-failed hostapd dnsmasq mosquitto >/dev/null 2>&1 || true
sudo systemctl restart hostapd
sleep 2
sudo systemctl restart dnsmasq
sudo systemctl restart mosquitto

if ! ip -4 addr show dev "$AP_IFACE" | grep -q '192\.168\.10\.1/24'; then
  echo "ERROR: $AP_IFACE no quedo con IP 192.168.10.1/24"
  ip addr show "$AP_IFACE" || true
  exit 1
fi

for service in hostapd dnsmasq mosquitto; do
  if ! systemctl is-active --quiet "$service"; then
    echo "ERROR: $service no quedo activo"
    systemctl status "$service" --no-pager -l || true
    exit 1
  fi
done

if command -v iw >/dev/null 2>&1 && ! iw dev "$AP_IFACE" info 2>/dev/null | grep -q 'type AP'; then
  echo "ERROR: $AP_IFACE no quedo en modo AP"
  iw dev "$AP_IFACE" info || true
  systemctl status hostapd --no-pager -l || true
  exit 1
fi

python3 -m pip install -r "$ROOT_DIR/requirements.txt" --break-system-packages || python3 -m pip install -r "$ROOT_DIR/requirements.txt"

echo "Listo: SSID=$SSID IP=192.168.10.1 MQTT=1883 canal=$AP_CHANNEL en interfaz $AP_IFACE. Internet/SSH queda en $WLAN_IFACE."
