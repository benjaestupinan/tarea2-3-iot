# Tarea 2

**Diseño de Sistemas IoT**  
Universidad de Chile  
Facultad de Ciencias Físicas y Matemáticas  
Departamento de Ciencias de la Computación

**Profesor:** Luciano Radrigán F.  
**Ayudante:** Lucas Llort

**Fecha de publicación:** lunes 8 de junio de 2026.  
**Parte A - entrega:** domingo 22 de junio de 2026 a las 23:59.  
**Parte B - entrega:** miércoles 8 de julio de 2026 a las 23:59 (nueva fecha).

## Abstract

Desarrollar un sistema IoT de adquisición, transporte y visualización de datos basado en MQTT con serialización Protocol Buffers (Protobuf). La Raspberry Pi 4 actuará como punto de acceso Wi-Fi (AP), servidor DHCP, broker MQTT (Mosquitto), publicador de mensajes y panel de configuración dinámica del sistema.

Un ESP32 (ESP32-B) se conectará a la red Wi-Fi generada por la Raspberry Pi y actuará exclusivamente como suscriptor MQTT que recibe y decodifica los mensajes publicados. Los datos de todos los sensores se simulan por software en la Raspberry Pi. El nivel de QoS de cada tópico y la selección de sensores activos son configurables en tiempo de ejecución desde la Raspberry Pi. Los sensores simulados son: acelerómetro triaxial y temperatura.

Adicionalmente, Wireshark debe estar abierto durante la operación del sistema para capturar y analizar el tráfico MQTT en la red.

La arquitectura general del sistema es la siguiente:

```text
[Raspberry Pi 4 (AP + DHCP + Broker MQTT + Publicador + Config)]
                   ↓ Wi-Fi / MQTT
            [ESP32-B (Suscriptor)]
```

Esta tarea se divide en dos partes con fechas de entrega distintas, descritas al final del documento.

## 1. Infraestructura de Red en Raspberry Pi 4

La Raspberry Pi 4 debe configurarse como punto de acceso Wi-Fi con servidor DHCP integrado, de modo que el ESP32 obtenga dirección IP automáticamente al conectarse. Esta configuración debe quedar documentada y ser reproducible mediante un script de instalación incluido en el repositorio.

### 1.1 Punto de Acceso Wi-Fi (hostapd)

Configurar la interfaz `wlan0` (o la disponible) como AP con los siguientes parámetros mínimos:

- **SSID y contraseña:** deben corresponder a las credenciales propias de cada grupo, definidas en `config.json` (campos `wifi_ssid` y `wifi_password`). No se permite usar valores genéricos o por defecto.
- **Banda:** 2.4 GHz, canal 6.
- **Seguridad:** WPA2-PSK.
- **Máximo de clientes:** 5.

### 1.2 Servidor DHCP (dnsmasq)

Configurar `dnsmasq` para asignar direcciones IP dinámicas dentro del rango `192.168.10.100-192.168.10.150`, con los siguientes parámetros:

- IP estática de la Raspberry Pi en la interfaz AP: `192.168.10.1`.
- Tiempo de lease: 12 horas.
- Opción DNS: `8.8.8.8` (Google) o `1.1.1.1` (Cloudflare).
- Registrar en el log las asignaciones DHCP con timestamp y dirección MAC.

El archivo de configuración `/etc/dnsmasq.conf` debe incluirse en el repositorio bajo `/raspberry/network/`.

### 1.3 Broker MQTT (Mosquitto)

Instalar y configurar Mosquitto como broker MQTT local:

- Puerto por defecto: `1883` (sin TLS para esta tarea).
- Listener vinculado a la IP del AP (`192.168.10.1`).
- `allow_anonymous true` (autenticación no requerida).
- Habilitar logging de conexiones y mensajes en `/var/log/mosquitto/mosquitto.log`.
- El archivo `mosquitto.conf` debe incluirse en `/raspberry/network/`.

### 1.4 Captura de tráfico con Wireshark

Durante toda la operación del sistema, Wireshark debe estar abierto en la Raspberry Pi capturando el tráfico en la interfaz AP (`wlan0`). Se debe aplicar el filtro de captura `tcp.port == 1883` para aislar el tráfico MQTT.

- Wireshark debe estar visible en el video de demostración, mostrando los paquetes MQTT `PUBLISH`, `SUBSCRIBE` y `CONNECT` en tiempo real.
- Al cambiar la configuración dinámica (QoS o sensores activos), el cambio debe ser observable en la captura de Wireshark: los paquetes `PUBLISH` deben reflejar el nuevo nivel de QoS y los tópicos activos deben cambiar acorde.
- Incluir en el README una captura de pantalla de Wireshark mostrando al menos un mensaje `PUBLISH` de cada tópico, con el campo QoS visible.

## 2. Configuración Dinámica desde la Raspberry Pi

Uno de los requisitos centrales de esta tarea es que tanto el nivel de QoS de cada tópico como la selección de sensores activos sean configurables en tiempo de ejecución, sin necesidad de reiniciar el sistema ni modificar archivos manualmente.

### 2.1 Archivo de configuración (`config.json`)

Toda la configuración del sistema reside en un único archivo `config.json` en `/raspberry/`. A continuación se muestra la estructura mínima requerida:

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

**Listing 1:** Estructura mínima de `config.json`.

Los campos relevantes son:

- `sensors.<nombre>.enabled`: activa o desactiva la publicación de ese sensor (`true`/`false`).
- `sensors.<nombre>.qos`: nivel de QoS MQTT para ese tópico (valores válidos: 0, 1 o 2).
- `sensors.<nombre>.rate_hz`: frecuencia de muestreo en Hz (solo informativa; el publicador la lee al iniciar).

### 2.2 Panel de configuración en la interfaz gráfica

La interfaz PyQt5 debe incorporar una pestaña adicional llamada **Configuración** con los siguientes controles:

1. Para cada sensor (acelerómetro, temperatura):

- Un `QCheckBox` para activar o desactivar el sensor.
- Un `QComboBox` con las opciones de QoS: 0, 1, 2.

2. Un botón **Aplicar** que:

- Escribe los cambios en `config.json`.
- Notifica al publicador MQTT mediante una señal interna (por ejemplo, `asyncio.Event`) para que este relance las corutinas afectadas con el nuevo QoS y habilite o deshabilite los tópicos correspondientes.

3. Un botón **Recargar** que lee el estado actual de `config.json` y actualiza los controles de la UI sin aplicar cambios.

El cambio de configuración debe ser observable en Wireshark sin reiniciar el sistema: al desactivar un sensor, su tópico debe dejar de aparecer en la captura; al cambiar el QoS, los paquetes `PUBLISH` deben reflejar el nuevo valor.

## 3. Serialización con Protocol Buffers

Todos los mensajes intercambiados vía MQTT deben serializarse usando Protocol Buffers (Protobuf). El archivo `.proto` que define los mensajes es la fuente de verdad y debe incluirse en `/proto/` en la raíz del repositorio.

### 3.1 Archivo `.proto`

Definir los siguientes tipos de mensaje en un único archivo `sensors.proto` (sintaxis `proto3`):

```proto
syntax = "proto3";
package iot;

message AccelSample {
  uint32 timestamp_ms = 1;
  float ax = 2;
  float ay = 3;
  float az = 4;
}

message TempSample {
  uint32 timestamp_ms = 1;
  float temperature = 2;
}

message SensorEnvelope {
  string source_id = 1;
  oneof payload {
    AccelSample accel = 2;
    TempSample temp = 3;
  }
}
```

**Listing 2:** `sensors.proto`.

El campo `source_id` identifica el origen del dato y será siempre `"rpi4"`, ya que la Raspberry Pi es el único publicador del sistema. El mensaje `SensorEnvelope` es el único tipo publicado en MQTT; contiene exactamente un payload mediante el mecanismo `oneof`.

### 3.2 Generación de código

Generar código a partir del `.proto` para los dos lenguajes usados:

- **Python (Raspberry Pi):** usando `protoc` con el plugin estándar. Incluir los archivos generados (`*_pb2.py`) en `/raspberry/proto/`.
- **C (ESP32-B):** usando nanopb, implementación de Protobuf para microcontroladores. Incluir los archivos generados (`sensors.pb.h`, `sensors.pb.c`) en `/esp32-sub/main/proto/`. Documentar la versión de nanopb usada.

El README debe incluir los comandos exactos para generar el código en cada plataforma.

## 4. Publicador MQTT en Raspberry Pi (Python)

La Raspberry Pi es el único publicador MQTT del sistema. Simula dos sensores por software y publica sus datos en los tópicos correspondientes usando `paho-mqtt` y el módulo Protobuf generado. El nivel de QoS y la lista de sensores activos se leen de `config.json` en tiempo de ejecución.

### 4.1 Sensor de acelerómetro simulado

Mismo modelo de simulación que en la Tarea 1 (sinusoide con ruido, rango ±16 g, ejes secundarios atenuados un 30%):

- Frecuencia de muestreo: 50 Hz (una muestra cada 20 ms).
- Tópico: `iot/rpi4/accel`.
- QoS: configurable desde `config.json` (campo `sensors.accel.qos`).

### 4.2 Sensor de temperatura simulada

Mismo modelo de la Tarea 1 (oscilación lenta entre 20 °C y 30 °C):

- Frecuencia de muestreo: una muestra cada 15 segundos.
- Tópico: `iot/rpi4/temp`.
- QoS: configurable desde `config.json` (campo `sensors.temp.qos`).

### 4.3 Tópicos MQTT

| Tópico | Sensor | Frecuencia | QoS | Payload |
| --- | --- | --- | --- | --- |
| `iot/rpi4/accel` | Acelerómetro | 50 Hz | configurable | `SensorEnvelope` (Protobuf) |
| `iot/rpi4/temp` | Temperatura | 1/15 Hz | configurable | `SensorEnvelope` (Protobuf) |
| `iot/status/rpi4` | Heartbeat | 0.1 Hz | 1 (fijo) | JSON `{ "status", "ts" }` |

**Table 1:** Tópicos publicados por la Raspberry Pi (único publicador del sistema). El QoS de los dos primeros es configurable en tiempo de ejecución. Solo acelerómetro y temperatura.

El heartbeat en `iot/status/rpi4` es el único mensaje en JSON y su QoS es fijo en 1; todos los demás deben serializarse con Protobuf.

### 4.4 Requisitos del publicador

- Implementar cada sensor en una corutina `asyncio` independiente.
- Usar `asyncio.gather` para ejecutar todas las corutinas simultáneamente.
- Al recibir una señal de reconfiguración (desde la GUI), cancelar y relanzar las corutinas afectadas con el nuevo QoS o activación.
- Reconexión automática al broker si se pierde la conexión.
- Registrar en consola el número de mensajes publicados por tópico cada 10 segundos.

## 5. Suscriptor MQTT en ESP32-B (ESP-IDF en C)

El ESP32-B es el único microcontrolador del sistema y debe conectarse a la red Wi-Fi de la Raspberry Pi, suscribirse a los tópicos MQTT y deserializar los mensajes Protobuf usando nanopb. ESP32-B actúa únicamente como receptor; no publica datos propios.

### 5.1 Conexión Wi-Fi

- Conectarse al SSID de la Raspberry Pi usando `esp_wifi.h` de ESP-IDF.
- SSID y contraseña deben corresponder a las credenciales propias de cada grupo, definidas en `config.json` (campos `wifi_ssid` y `wifi_password`). No se permite usar valores genéricos o por defecto.
- Reconexión automática con backoff exponencial (hasta 5 reintentos, espera máxima 60 s).
- Registrar la dirección IP asignada por DHCP en el log de arranque.

### 5.2 Cliente MQTT

- Usar `esp_mqtt_client` de ESP-IDF (componente `mqtt`).
- Broker URI: `mqtt://192.168.10.1:1883` (configurable en `config.json`, campo `mqtt_broker_uri`).
- Suscribirse a: `iot/rpi4/accel`, `iot/rpi4/temp` y `iot/status/rpi4`.
- Manejar los eventos `MQTT_EVENT_CONNECTED`, `MQTT_EVENT_DISCONNECTED` y `MQTT_EVENT_DATA`.

### 5.3 Deserialización con nanopb

Usar nanopb para decodificar los mensajes `SensorEnvelope` recibidos. Función sugerida en C (puede modificarse):

```c
#include "sensors.pb.h"
#include <pb_decode.h>

void handle_mqtt_data(const char *topic,
                      const uint8_t *data, int len) {
  iot_SensorEnvelope env = iot_SensorEnvelope_init_zero;
  pb_istream_t stream = pb_istream_from_buffer(data, len);

  if (!pb_decode(&stream, iot_SensorEnvelope_fields, &env)) {
    ESP_LOGE(TAG, "Decode failed: %s",
             PB_GET_ERROR(&stream));
    return;
  }

  if (env.which_payload == iot_SensorEnvelope_accel_tag) {
    ESP_LOGI(TAG, "Accel: ax=%.2f ay=%.2f az=%.2f",
             env.payload.accel.ax,
             env.payload.accel.ay,
             env.payload.accel.az);
  } else if (env.which_payload == iot_SensorEnvelope_temp_tag) {
    ESP_LOGI(TAG, "Temp: %.1f C",
             env.payload.temp.temperature);
  }
}
```

**Listing 3:** Deserialización con nanopb.

### 5.4 Salida por puerto serie

ESP32-B debe imprimir por UART0 (115200 baud) un resumen legible de cada mensaje recibido con el siguiente formato:

```text
[ACCEL] src=rpi4 ts=12345ms ax=+3.14 ay=-1.07 az=+0.88
[TEMP]  src=rpi4 ts=15000ms temp=24.3C
```

**Listing 4:** Formato de salida UART.

Requisitos mínimos del firmware:

- Usar `esp_mqtt_client` y `esp_wifi` de ESP-IDF.
- Una tarea FreeRTOS (`iot_subscriber_task`) que gestione la recepción y el log.
- Mostrar contador acumulado de mensajes recibidos por tópico cada 30 segundos.
- Documentar en el README la dirección MAC y el nombre de red al que se conecta ESP32-B.

## 6. Interfaz Gráfica en Raspberry Pi (Python: PyQt5 + pyqtgraph)

La interfaz gráfica de la Tarea 1 debe extenderse para soportar los nuevos sensores MQTT. Se mantiene la base PyQt5 + pyqtgraph, incorporando el panel de Configuración descrito en la Sección 2.2.

### 6.1 Arquitectura de la interfaz

- Separar la lógica MQTT (`paho-mqtt` en hilo propio) de la lógica gráfica (hilo Qt principal) usando señales Qt (`pyqtSignal`).
- Los callbacks MQTT emiten señales; los slots Qt actualizan la UI. No llamar directamente a widgets desde hilos ajenos a Qt.

### 6.2 Paneles requeridos

La interfaz debe implementar los siguientes paneles mediante `QTabWidget`:

1. **Panel Acelerómetro:** gráfico de líneas con ventana deslizante configurable (mínimo 2 s) de los tres ejes (Ax, Ay, Az). Indicadores estadísticos calculados sobre ventana de 1000 muestras a 50 Hz (= 20 s): RMS por eje, peak positivo por eje, distancia pico a pico por eje.
2. **Panel Temperatura:** indicador numérico del último valor con timestamp, y gráfico histórico de los últimos 30 valores.
3. **Panel Estado:** tabla con columnas Tópico, QoS activo, Último mensaje (s atrás), Mensajes recibidos, que se actualice cada segundo. Dos filas: acelerómetro y temperatura.
4. **Panel Configuración:** controles para activar/desactivar sensores y cambiar el QoS de cada tópico en tiempo de ejecución, descrito en la Sección 2.2.

### 6.3 Guardado de datos

Botón para iniciar/detener el registro. Los datos deben guardarse en un archivo CSV con las siguientes columnas:

```csv
timestamp_ms,source,topic,qos,ax,ay,az,temperature
```

Las columnas que no apliquen para un mensaje dado deben dejarse vacías. La columna `qos` registra el nivel de QoS efectivo del mensaje.

Librerías sugeridas: `paho-mqtt`, `PyQt5`, `pyqtgraph`, `numpy`, `asyncio`, `protobuf`.

## 7. Formato de Mensajes Protobuf

La siguiente tabla resume el tamaño estimado en bytes de cada mensaje serializado (Protobuf wire format, sin compresión):

| Mensaje | Campos | Tamaño est. |
| --- | --- | --- |
| `AccelSample` | `timestamp(4) + ax(4) + ay(4) + az(4)` | ≈ 20 bytes |
| `TempSample` | `timestamp(4) + temp(4)` | ≈ 12 bytes |
| `SensorEnvelope (accel)` | `source_id(var) + AccelSample` | ≈ 28-32 bytes |

**Table 2:** Tamaño estimado de mensajes Protobuf.

Comparar el tamaño de los mensajes Protobuf contra una representación JSON equivalente y reportar el ratio de compresión en el README. Ejemplo esperado: `AccelSample` en JSON (≈ 80 bytes) vs Protobuf (≈ 20 bytes) supone un factor ≈ 4× de reducción.

Si se opta por otro formato de serialización (CBOR, MessagePack, etc.), debe justificarse y documentarse completamente en el README.

# Parte A

**Plazo:** domingo 22 de junio de 2026 a las 23:59  
**Entrega asincrónica - sin demostración en vivo**

La Parte A cubre la implementación base del sistema y se entrega mediante un video y el repositorio de código. No se realiza demostración en vivo en esta etapa.

Los requisitos mínimos que deben estar operativos en la Parte A son:

- Infraestructura de red funcionando: AP Wi-Fi, DHCP y broker Mosquitto en la Raspberry Pi.
- Publicador Python (`publisher.py`) publicando datos simulados de acelerómetro y temperatura en Protobuf, con QoS y activación de sensores leídos desde `config.json`.
- Interfaz gráfica (`gui.py`) con los cuatro paneles funcionando, incluyendo el Panel Configuración con botones Aplicar y Recargar.
- Firmware del ESP32-B compilando y ejecutándose: conectándose al AP, suscribiéndose a los tópicos e imprimiendo por serie los mensajes deserializados con nanopb.
- Guardado de datos en CSV operativo.
- Wireshark capturando tráfico MQTT con filtro `tcp.port == 1883`.

En la Parte A no se evalúa la robustez ante fallos ni la integración perfecta de todos los componentes en tiempo real; se acepta que algunos elementos funcionen de forma parcial siempre que sean demostrables en el video.

## 8. Entregables Parte A

1. Repositorio Git con la siguiente estructura:

- `/proto/sensors.proto`: fuente de verdad Protobuf.
- `/esp32-sub/`: firmware ESP32-B en ESP-IDF con `CMakeLists.txt` funcional y archivos nanopb generados en `/esp32-sub/main/proto/`.
- `/raspberry/publisher.py`: publicador MQTT con soporte de configuración dinámica de QoS y sensores activos.
- `/raspberry/gui.py`: interfaz gráfica con los cuatro paneles (incluido el Panel Configuración).
- `/raspberry/proto/`: archivos `*_pb2.py` generados.
- `/raspberry/network/`: `hostapd.conf`, `dnsmasq.conf`, `mosquitto.conf`.
- `/raspberry/config.json`: con credenciales del grupo y configuración de sensores y QoS.
- `requirements.txt`.
- `README.md` con:
- Descripción de la arquitectura del sistema.
- Instrucciones de instalación del AP, DHCP y Mosquitto.
- Comandos para generar el código Protobuf (Python y nanopb).
- Instrucciones de compilación y flash del firmware ESP32-B.
- Instrucciones de ejecución del publicador y la GUI.
- Tabla comparativa de tamaños Protobuf vs JSON.
- Dirección MAC del ESP32-B y nombre de red Wi-Fi del grupo.
- Captura de pantalla de Wireshark mostrando paquetes `PUBLISH` de cada tópico con QoS visible.
- Capturas de pantalla de los cuatro paneles de la interfaz.

2. Video de demostración (máximo 5 minutos) que muestre:

- La asignación DHCP al ESP32-B (dirección IP visible en el log serie).
- El flujo completo de un mensaje: simulación en la Raspberry Pi → publicación MQTT → recepción y log en ESP32-B.
- Los cuatro paneles de la interfaz gráfica funcionando simultáneamente.
- El Panel Configuración en uso: cambiar el QoS de un tópico y desactivar un sensor; el efecto debe ser visible tanto en la GUI como en Wireshark (mostrar ambas ventanas en el video).
- Wireshark abierto en la Raspberry Pi con el filtro `tcp.port == 1883` activo, mostrando el cambio de paquetes al reconfigurar.
- El guardado de datos en CSV activo.

# Parte B

**Plazo:** miércoles 8 de julio de 2026 a las 23:59 (nueva fecha)  
**Entrega mediante video de demostración - sin sesión en vivo**

La Parte B requiere que el sistema de la Parte A esté completamente funcional e integrado: todos los componentes deben operar en conjunto sin intervención manual durante la grabación. Se puede incorporar correcciones al código de la Parte A antes de la entrega.

La diferencia central respecto a la Parte A es la siguiente:

- **Integración en tiempo real:** la reconfiguración dinámica (cambio de QoS, activar/desactivar sensores) debe verse reflejada simultáneamente en el publicador, la GUI y Wireshark sin reiniciar ningún proceso.
- **Robustez:** reconexión automática del ESP32-B y del publicador ante desconexiones del broker; el sistema debe recuperarse solo.
- **Demostración en video:** el video debe grabarse en una sola toma continua (sin cortes de edición) mostrando la reconfiguración dinámica en acción: cambio de QoS, activación/desactivación de sensores y una desconexión/reconexión del ESP32-B, tal como lo pediría el ayudante en una demostración en vivo.
- **Revisión de código:** el video debe incluir una explicación narrada de la implementación de cualquier módulo relevante (publicador, firmware, GUI), a modo de respuesta a las preguntas que el ayudante habría formulado en una instancia presencial.

En resumen: la Parte A valida que los componentes individuales existen y funcionan; la Parte B valida, mediante un video íntegro y sin cortes, que el sistema completo opera de forma integrada y robusta.

## 9. Entregables Parte B

1. Repositorio Git actualizado con todas las correcciones posteriores a la Parte A. El historial de commits debe reflejar los cambios realizados entre ambas entregas.

2. Video de demostración (máximo 20 minutos, grabado en una sola toma continua, sin cortes de edición) que debe cubrir obligatoriamente:

### a) Arranque completo del sistema desde cero

- Iniciar el AP Wi-Fi y el servidor DHCP en la Raspberry Pi.
- Conectar el ESP32-B y verificar la asignación de IP en el log serie.
- Arrancar el broker Mosquitto y el publicador Python.

### b) Demostración de la configuración dinámica en vivo

- Cambiar el QoS del acelerómetro de 0 a 2 desde el Panel Configuración y mostrar el cambio en Wireshark.
- Desactivar el sensor de temperatura y verificar que su tópico desaparece de la captura de Wireshark y del Panel Estado.
- Reactivar el sensor de temperatura y verificar la reanudación.

### c) Revisión del código fuente narrada en el mismo video

- Explicar la lógica de reconfiguración dinámica en el publicador Python (`publisher.py`).
- Mostrar la deserialización Protobuf en el firmware ESP32-B (`handle_mqtt_data`).
- Explicar el mecanismo de señales Qt entre el hilo MQTT y la GUI.
