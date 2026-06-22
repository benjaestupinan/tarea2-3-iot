# Tarea 2 IoT

Sistema base para la Parte A: Raspberry Pi como AP, DHCP, broker Mosquitto, publicador MQTT con Protobuf y GUI PyQt5. El ESP32-B queda en `esp32/` para que se adapte como suscriptor MQTT con nanopb.

## Estructura

- `raspberry/`: configuracion de red, publicador MQTT, GUI y Protobuf Python.
- `proto/sensors.proto`: interfaz Protobuf fuente de verdad.
- `esp32/`: firmware ESP32 en ESP-IDF.
- `requirements.txt`: dependencias Python para Raspberry.

## Raspberry

Credenciales configuradas en `raspberry/config.json`:

```json
{
  "wifi_ssid": "IoT_Grupo07",
  "wifi_password": "pMo!3oN3c7Fzx$xVgkKYF",
  "mqtt_broker_uri": "mqtt://192.168.10.1:1883"
}
```

Instalacion en Raspberry:

```bash
cd raspberry
chmod +x network/install_raspberry.sh network/restore_wifi.sh
./network/install_raspberry.sh
```

Para volver a usar `wlan0` como WiFi normal:

```bash
./network/restore_wifi.sh
```

Ejecucion:

```bash
cd raspberry
python3 publisher.py
```

En otra terminal:

```bash
cd raspberry
python3 gui.py
```

Wireshark: capturar en `wlan0` con filtro `tcp.port == 1883`.

## ESP32-B

El firmware del suscriptor esta en `esp32/esp-sub`.

Compilar:

```bash
cd esp32/esp-sub
idf.py set-target esp32
idf.py build
```

Subir al ESP32:

```bash
idf.py flash
```

Ver la salida por serie:

```bash
idf.py monitor
```

Tambien se puede hacer todo junto:

```bash
idf.py set-target esp32 build flash monitor
```

Para salir del monitor: `Ctrl+]`.

## Protobuf

Regenerar Python:

```bash
python3 -m grpc_tools.protoc -Iproto --python_out=raspberry/proto proto/sensors.proto
```

Regenerar C/nanopb para ESP32 cuando corresponda:

```bash
nanopb_generator proto/sensors.proto --output-dir=esp32/esp-sub/main/proto
```

## Topicos MQTT

| Topico | Payload | QoS |
| --- | --- | --- |
| `iot/rpi4/accel` | `SensorEnvelope.accel` Protobuf | configurable |
| `iot/rpi4/temp` | `SensorEnvelope.temp` Protobuf | configurable |
| `iot/status/rpi4` | JSON heartbeat | 1 fijo |
