#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo systemctl restart dnsmasq hostapd mosquitto
echo "Servicios reiniciados. En otra terminal ejecuta:"
echo "cd $ROOT_DIR && python3 publisher.py"
echo "cd $ROOT_DIR && python3 gui.py"
echo "Wireshark: interfaz wlan0, filtro tcp.port == 1883"
