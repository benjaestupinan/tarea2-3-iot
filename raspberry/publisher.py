import asyncio
import json
import math
import random
import time
from pathlib import Path
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from proto import sensors_pb2

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
SOURCE_ID = "rpi4"
TOPICS = {"accel": "iot/rpi4/accel", "temp": "iot/rpi4/temp"}
HEARTBEAT_TOPIC = "iot/status/rpi4"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    for name in ("accel", "temp"):
        sensor = cfg["sensors"][name]
        sensor["enabled"] = bool(sensor.get("enabled", False))
        sensor["qos"] = max(0, min(2, int(sensor.get("qos", 0))))
    return cfg


def broker_from_uri(uri):
    parsed = urlparse(uri)
    return parsed.hostname or "192.168.10.1", parsed.port or 1883


def make_client():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.on_connect = lambda _c, _u, _f, rc, *args: print(f"MQTT conectado rc={rc}")
    client.on_disconnect = lambda _c, _u, rc, *args: print(f"MQTT desconectado rc={rc}")
    return client


async def connect_loop(client, cfg):
    host, port = broker_from_uri(cfg["mqtt_broker_uri"])
    while True:
        try:
            client.connect(host, port, keepalive=30)
            client.loop_start()
            return
        except OSError as exc:
            print(f"No se pudo conectar a {host}:{port}: {exc}; reintento en 2 s")
            await asyncio.sleep(2)


def timestamp_ms():
    return int(time.monotonic() * 1000) & 0xFFFFFFFF


async def publish_accel(client, qos, counters):
    topic = TOPICS["accel"]
    start = time.monotonic()
    while True:
        t = time.monotonic() - start
        ax = 12.0 * math.sin(2.0 * math.pi * 1.0 * t) + random.uniform(-0.25, 0.25)
        ay = 0.3 * ax + random.uniform(-0.15, 0.15)
        az = 0.3 * 9.8 * math.cos(2.0 * math.pi * 0.5 * t) + random.uniform(-0.15, 0.15)
        ax, ay, az = [max(-16.0, min(16.0, v)) for v in (ax, ay, az)]
        env = sensors_pb2.SensorEnvelope(
            source_id=SOURCE_ID,
            accel=sensors_pb2.AccelSample(timestamp_ms=timestamp_ms(), ax=ax, ay=ay, az=az),
        )
        client.publish(topic, env.SerializeToString(), qos=qos)
        counters[topic] = counters.get(topic, 0) + 1
        await asyncio.sleep(0.02)


async def publish_temp(client, qos, counters):
    topic = TOPICS["temp"]
    start = time.monotonic()
    while True:
        t = time.monotonic() - start
        temp = 25.0 + 5.0 * math.sin(2.0 * math.pi * t / 120.0) + random.uniform(-0.15, 0.15)
        env = sensors_pb2.SensorEnvelope(
            source_id=SOURCE_ID,
            temp=sensors_pb2.TempSample(timestamp_ms=timestamp_ms(), temperature=temp),
        )
        client.publish(topic, env.SerializeToString(), qos=qos)
        counters[topic] = counters.get(topic, 0) + 1
        await asyncio.sleep(15.0)


async def publish_heartbeat(client, counters):
    while True:
        payload = json.dumps({"status": "ok", "ts": int(time.time())})
        client.publish(HEARTBEAT_TOPIC, payload, qos=1)
        counters[HEARTBEAT_TOPIC] = counters.get(HEARTBEAT_TOPIC, 0) + 1
        await asyncio.sleep(10.0)


async def log_counters(counters):
    last = {}
    while True:
        await asyncio.sleep(10.0)
        parts = []
        for topic, total in counters.items():
            parts.append(f"{topic}: +{total - last.get(topic, 0)} total={total}")
            last[topic] = total
        print("Publicados ultimos 10 s | " + " | ".join(parts))


async def manage_sensors(client, counters):
    tasks = {}
    active_cfg = {}
    config_mtime = None
    factories = {"accel": publish_accel, "temp": publish_temp}

    while True:
        try:
            mtime = CONFIG_PATH.stat().st_mtime
            if mtime != config_mtime:
                cfg = load_config()
                config_mtime = mtime
                for name, factory in factories.items():
                    sensor_cfg = cfg["sensors"][name]
                    desired = (sensor_cfg["enabled"], sensor_cfg["qos"])
                    if active_cfg.get(name) == desired:
                        continue
                    if name in tasks:
                        tasks[name].cancel()
                        try:
                            await tasks[name]
                        except asyncio.CancelledError:
                            pass
                        del tasks[name]
                    active_cfg[name] = desired
                    if sensor_cfg["enabled"]:
                        print(f"Activando {name} qos={sensor_cfg['qos']}")
                        tasks[name] = asyncio.create_task(factory(client, sensor_cfg["qos"], counters))
                    else:
                        print(f"Desactivando {name}")
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"Config invalida: {exc}")
        await asyncio.sleep(1.0)


async def main():
    cfg = load_config()
    client = make_client()
    counters = {}
    await connect_loop(client, cfg)
    try:
        await asyncio.gather(
            manage_sensors(client, counters),
            publish_heartbeat(client, counters),
            log_counters(counters),
        )
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Publicador detenido")
