#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include <esp_event.h>
#include <esp_log.h>
#include <esp_netif.h>
#include <esp_system.h>
#include <esp_wifi.h>
#include <mqtt_client.h>
#include <nvs_flash.h>

#include <pb_decode.h>
#include "sensors.pb.h"

#define WIFI_AP_SSID "IoT_Grupo07"
#define WIFI_AP_PASS "pMo!3oN3c7Fzx$xVgkKYF"

#define MQTT_BROKER_URI "mqtt://192.168.10.1:1883"
#define TOPIC_ACCEL "iot/rpi4/accel"
#define TOPIC_TEMP "iot/rpi4/temp"
#define TOPIC_STATUS "iot/status/rpi4"

static const char *TAG = "esp32-sub";

const uint8_t max_retries = 5;
uint8_t retries = 0;

SemaphoreHandle_t sem;
static uint32_t accel_count = 0;
static uint32_t temp_count = 0;
static uint32_t status_count = 0;

typedef struct {
  char *buffer;
  size_t size;
} string_decode_ctx_t;

static bool decode_string(pb_istream_t *stream, const pb_field_t *field,
                          void **arg) {
  (void)field;
  string_decode_ctx_t *ctx = (string_decode_ctx_t *)(*arg);
  size_t len = stream->bytes_left;

  if (len >= ctx->size) {
    len = ctx->size - 1;
  }

  if (!pb_read(stream, (pb_byte_t *)ctx->buffer, len)) {
    return false;
  }

  ctx->buffer[len] = '\0';

  if (stream->bytes_left > 0) {
    return pb_read(stream, NULL, stream->bytes_left);
  }

  return true;
}

static bool topic_matches(const esp_mqtt_event_t *event, const char *topic) {
  size_t topic_len = strlen(topic);
  return event->topic_len == topic_len &&
         strncmp(event->topic, topic, topic_len) == 0;
}

static void handle_protobuf_message(const char *topic, const uint8_t *data,
                                    int len) {
  char source_id[32] = "";
  string_decode_ctx_t source_ctx = {
      .buffer = source_id,
      .size = sizeof(source_id),
  };

  iot_SensorEnvelope env = iot_SensorEnvelope_init_zero;
  env.source_id.funcs.decode = decode_string;
  env.source_id.arg = &source_ctx;

  pb_istream_t stream = pb_istream_from_buffer(data, len);
  if (!pb_decode(&stream, iot_SensorEnvelope_fields, &env)) {
    ESP_LOGE(TAG, "Decode failed on %s: %s", topic, PB_GET_ERROR(&stream));
    return;
  }

  if (env.which_payload == iot_SensorEnvelope_accel_tag) {
    accel_count++;
    ESP_LOGI(TAG, "[ACCEL] src=%s ts=%lums ax=%+.2f ay=%+.2f az=%+.2f",
             source_id, (unsigned long)env.payload.accel.timestamp_ms,
             env.payload.accel.ax, env.payload.accel.ay, env.payload.accel.az);
  } else if (env.which_payload == iot_SensorEnvelope_temp_tag) {
    temp_count++;
    ESP_LOGI(TAG, "[TEMP]  src=%s ts=%lums temp=%.1fC", source_id,
             (unsigned long)env.payload.temp.timestamp_ms,
             env.payload.temp.temperature);
  } else {
    ESP_LOGW(TAG, "Mensaje Protobuf sin payload conocido en %s", topic);
  }
}

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data) {
  (void)handler_args;
  (void)base;
  esp_mqtt_event_t *event = event_data;

  switch (event_id) {
  case MQTT_EVENT_CONNECTED:
    ESP_LOGI(TAG, "Conectado al broker MQTT");
    esp_mqtt_client_subscribe(event->client, TOPIC_ACCEL, 0);
    esp_mqtt_client_subscribe(event->client, TOPIC_TEMP, 0);
    esp_mqtt_client_subscribe(event->client, TOPIC_STATUS, 0);
    break;

  case MQTT_EVENT_DISCONNECTED:
    ESP_LOGW(TAG, "Desconectado del broker MQTT");
    break;

  case MQTT_EVENT_DATA:
    if (topic_matches(event, TOPIC_ACCEL)) {
      handle_protobuf_message(TOPIC_ACCEL, (const uint8_t *)event->data,
                              event->data_len);
    } else if (topic_matches(event, TOPIC_TEMP)) {
      handle_protobuf_message(TOPIC_TEMP, (const uint8_t *)event->data,
                              event->data_len);
    } else if (topic_matches(event, TOPIC_STATUS)) {
      status_count++;
      ESP_LOGI(TAG, "[STATUS] %.*s", event->data_len, event->data);
    }
    break;

  default:
    break;
  }
}

void event_handler(void *arg, esp_event_base_t event_base, int32_t event_id,
                   void *event_data) {
  (void)arg;

  if (event_base == WIFI_EVENT) {           // Solo nos importan 2 eventos
    if (event_id == WIFI_EVENT_STA_START) { // Cuando se inicializa el sistema
      esp_wifi_connect();
    } else if (event_id ==
               WIFI_EVENT_STA_DISCONNECTED) { // Cuando se desconecta
      ESP_LOGW(TAG, "Error al conectar, intento %d/%d", retries, max_retries);

      if (retries < max_retries) {
        esp_wifi_connect();
        retries++;
      } else {
        xSemaphoreGive(sem);
      }
    }
  } else if (event_base == IP_EVENT) {
    if (event_id == IP_EVENT_STA_GOT_IP) { // Se obtiene una IP (por DHCP)
      ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
      ESP_LOGI(TAG, "IP obtenida: " IPSTR, IP2STR(&event->ip_info.ip));
      ESP_LOGI(TAG, "Mascara: " IPSTR, IP2STR(&event->ip_info.netmask));
      ESP_LOGI(TAG, "Gateway: " IPSTR, IP2STR(&event->ip_info.gw));

      xSemaphoreGive(sem);
    }
  }
}

static void iot_subscriber_task(void *arg) {
  (void)arg;

  xSemaphoreTake(sem, portMAX_DELAY);

  if (retries >= max_retries) {
    ESP_LOGE(TAG, "Error al conectarse al AP %s, reiniciando", WIFI_AP_SSID);
    sleep(5);
    esp_restart();
  }

  ESP_LOGI(TAG, "Conectado con exito al AP %s", WIFI_AP_SSID);

  esp_mqtt_client_config_t mqtt_cfg = {
      .broker.address.uri = MQTT_BROKER_URI,
  };

  esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
  esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler,
                                 NULL);
  esp_mqtt_client_start(client);

  while (true) {
    vTaskDelay(pdMS_TO_TICKS(30000));
    ESP_LOGI(TAG,
             "Contadores 30s/acum: accel=%lu temp=%lu status=%lu",
             (unsigned long)accel_count, (unsigned long)temp_count,
             (unsigned long)status_count);
  }
}

void app_main() {
  sem = xSemaphoreCreateBinary();

  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  ESP_ERROR_CHECK(esp_netif_init());

  ESP_ERROR_CHECK(esp_event_loop_create_default());
  esp_netif_create_default_wifi_sta();

  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&cfg));

  esp_event_handler_instance_t wifi_any_evh;
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL, &wifi_any_evh));

  esp_event_handler_instance_t got_ip_evh;
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_STA_GOT_IP, &event_handler, NULL, &got_ip_evh));

  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  wifi_config_t wifi_config = {.sta = {
                                  .ssid = WIFI_AP_SSID,
                                  .password = WIFI_AP_PASS,
                                  .threshold.authmode = WIFI_AUTH_WPA2_PSK,
                                  .sae_pwe_h2e = WPA3_SAE_PWE_BOTH,
                                  .sae_h2e_identifier = "",
                              }};
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));

  ESP_ERROR_CHECK(esp_wifi_start());

  xTaskCreate(iot_subscriber_task, "iot_subscriber_task", 8192, NULL, 5, NULL);
}
