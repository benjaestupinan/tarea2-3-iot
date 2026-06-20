#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WLAN_IFACE="${WLAN_IFACE:-wlan0}"
AP_IP="192.168.10.1/24"
SSID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_ssid"])' "$ROOT_DIR/config.json")"
PASS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["wifi_password"])' "$ROOT_DIR/config.json")"

echo "Instalando paquetes base..."
sudo apt update
sudo apt install -y hostapd dnsmasq mosquitto mosquitto-clients wireshark python3-pip python3-pyqt5 python3-numpy

echo "Deteniendo servicios antes de configurar..."
sudo systemctl stop hostapd || true
sudo systemctl stop dnsmasq || true
sudo systemctl stop mosquitto || true

if ! ip link show "$WLAN_IFACE" >/dev/null 2>&1; then
  echo "No existe la interfaz $WLAN_IFACE. Ejecuta con WLAN_IFACE=tu_interfaz ./network/install_raspberry.sh"
  exit 1
fi

echo "Copiando configuraciones..."
sudo cp "$ROOT_DIR/network/hostapd.conf" /etc/hostapd/hostapd.conf
sudo sed -i "s/^ssid=.*/ssid=$SSID/" /etc/hostapd/hostapd.conf
sudo sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$PASS/" /etc/hostapd/hostapd.conf
sudo cp "$ROOT_DIR/network/dnsmasq.conf" /etc/dnsmasq.conf
sudo cp "$ROOT_DIR/network/mosquitto.conf" /etc/mosquitto/conf.d/iot.conf

# Evita conflictos con listeners por defecto en algunas instalaciones.
if [ -f /etc/mosquitto/conf.d/default.conf ]; then
  sudo mv /etc/mosquitto/conf.d/default.conf /etc/mosquitto/conf.d/default.conf.disabled
fi

sudo mkdir -p /var/log/mosquitto
sudo chown mosquitto:mosquitto /var/log/mosquitto || true

if ! grep -q '^DAEMON_CONF="/etc/hostapd/hostapd.conf"' /etc/default/hostapd; then
  echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' | sudo tee -a /etc/default/hostapd >/dev/null
fi

echo "Configurando IP estatica $AP_IP en $WLAN_IFACE..."
sudo rfkill unblock wifi || true
sudo ip addr flush dev "$WLAN_IFACE" || true
sudo ip addr add "$AP_IP" dev "$WLAN_IFACE"
sudo ip link set "$WLAN_IFACE" up

echo "Habilitando y reiniciando servicios..."
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl enable mosquitto
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq
sudo systemctl restart mosquitto || {
  echo "Mosquitto fallo. Diagnostico rapido:"
  sudo systemctl status mosquitto --no-pager || true
  sudo journalctl -xeu mosquitto --no-pager | tail -40 || true
  exit 1
}

echo "Instalando dependencias Python..."
python3 -m pip install -r "$ROOT_DIR/requirements.txt" --break-system-packages || python3 -m pip install -r "$ROOT_DIR/requirements.txt"

echo "Listo. SSID=$SSID, IP AP=192.168.10.1, broker MQTT=1883"
echo "Ejecuta: python3 publisher.py"
echo "En otra terminal: python3 gui.py"
echo "Wireshark: interfaz $WLAN_IFACE, filtro tcp.port == 1883"
