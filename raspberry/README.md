# Raspberry - Tarea 2 Parte A

Codigo de la Raspberry Pi para AP Wi-Fi, DHCP, broker Mosquitto, publicador MQTT Protobuf y GUI PyQt5.

## Archivos

- `config.json`: credenciales Wi-Fi, broker MQTT, sensores activos y QoS.
- `publisher.py`: simula acelerometro y temperatura, publica Protobuf por MQTT y heartbeat JSON.
- `gui.py`: paneles de acelerometro, temperatura, estado, configuracion y guardado CSV.
- `proto/sensors_pb2.py`: modulo Python Protobuf para `SensorEnvelope`.
- `network/hostapd.conf`: base de configuracion AP 2.4 GHz canal 6.
- `network/dnsmasq.conf`: DHCP `192.168.10.100-192.168.10.150`.
- `network/mosquitto.conf`: broker local en `192.168.10.1:1883`.
- `network/install_raspberry.sh`: instala servicios y copia configuraciones.
- `network/restore_wifi.sh`: desactiva el AP y devuelve `wlan0` a NetworkManager.

## Configuracion

Editar antes de instalar:

```bash
nano config.json
```

Cambiar obligatoriamente:

- `wifi_ssid`: nombre de red del grupo.
- `wifi_password`: clave WPA2 del grupo.

Ejemplo:

```json
{
  "wifi_ssid": "IoT_GrupoXX",
  "wifi_password": "clave_del_grupo",
  "mqtt_broker_uri": "mqtt://192.168.10.1:1883",
  "sensors": {
    "accel": { "enabled": true, "qos": 0, "rate_hz": 50 },
    "temp": { "enabled": true, "qos": 1, "rate_hz": 0.067 }
  }
}
```

## Instalacion Raspberry

Ejecutar en la Raspberry:

```bash
cd tarea2-3-iot/raspberry
chmod +x network/install_raspberry.sh network/restore_wifi.sh
./network/install_raspberry.sh
```

El script instala `hostapd`, `dnsmasq`, `mosquitto`, `wireshark` y dependencias Python. Tambien fija `wlan0` con IP `192.168.10.1/24` y deja esa interfaz sin administracion de NetworkManager para que no vuelva a conectarse como cliente WiFi.

Si la interfaz no es `wlan0`:

```bash
WLAN_IFACE=nombre_interfaz ./network/install_raspberry.sh
```

Para volver a usar `wlan0` como WiFi normal:

```bash
./network/restore_wifi.sh
```

## Ejecucion

Terminal 1:

```bash
cd tarea2-3-iot/raspberry
python3 publisher.py
```

Terminal 2:

```bash
cd tarea2-3-iot/raspberry
python3 gui.py
```

## Topicos

| Topico | Payload | QoS |
| --- | --- | --- |
| `iot/rpi4/accel` | `SensorEnvelope.accel` Protobuf | configurable |
| `iot/rpi4/temp` | `SensorEnvelope.temp` Protobuf | configurable |
| `iot/status/rpi4` | JSON `{ "status", "ts" }` | 1 fijo |

El publicador revisa cambios en `config.json` cada 1 segundo. Al usar el panel Configuracion de la GUI, el archivo se guarda y el publicador relanza las tareas de sensores afectadas.

## GUI

Paneles incluidos:

- `Acelerometro`: grafico Ax/Ay/Az y estadisticas RMS, peak y pico a pico sobre hasta 1000 muestras.
- `Temperatura`: ultimo valor y grafico de ultimas 30 muestras.
- `Estado`: topico, QoS recibido, tiempo desde ultimo mensaje y contador.
- `Configuracion`: activar/desactivar sensores y cambiar QoS 0/1/2 con botones Aplicar y Recargar.
- `CSV`: iniciar/detener guardado en `data_log.csv`.

Columnas CSV:

```csv
timestamp_ms,source,topic,qos,ax,ay,az,temperature
```

## Wireshark

Abrir Wireshark en la Raspberry sobre la interfaz AP, normalmente `wlan0`.

Filtro pedido:

```text
tcp.port == 1883
```

En el video se debe mostrar `PUBLISH` para `iot/rpi4/accel` e `iot/rpi4/temp`, con el QoS visible. Al cambiar QoS o desactivar sensores desde la GUI, el cambio debe verse en la captura.

## Screenshots

Agregar las capturas al README final de la entrega o a una carpeta `docs/`:

- Panel Acelerometro.
- Panel Temperatura.
- Panel Estado.
- Panel Configuracion.
- Panel CSV.
- Wireshark con `PUBLISH` de acelerometro y temperatura.

## Protobuf

El archivo fuente de verdad esperado por la tarea es `/proto/sensors.proto`. Para regenerar Python cuando exista ese archivo:

```bash
python3 -m grpc_tools.protoc -I../proto --python_out=proto ../proto/sensors.proto
```

Esta carpeta ya incluye `proto/sensors_pb2.py` compatible con los mensajes requeridos para que `publisher.py` y `gui.py` funcionen.

## Tamano Protobuf vs JSON

| Mensaje | Protobuf aprox. | JSON aprox. | Reduccion |
| --- | ---: | ---: | ---: |
| Acelerometro | 28-32 B | 80-100 B | 3x |
| Temperatura | 18-24 B | 50-70 B | 2.5x |
