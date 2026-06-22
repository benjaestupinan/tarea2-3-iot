file(GLOB_RECURSE nanopb_runtime "nanopb/*.c")

idf_component_register(
  SRCS
    "main.c"
    "proto/proto/sensors.pb.c"
    "${nanopb_runtime}"

  INCLUDE_DIRS
    "."
    "proto"
    "proto/proto"
    "nanopb"

  PRIV_REQUIRES
    esp_wifi
    esp_netif
    nvs_flash
    mqtt
)
