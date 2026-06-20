import csv
import json
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import paho.mqtt.client as mqtt
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from proto import sensors_pb2

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
CSV_PATH = BASE_DIR / "data_log.csv"
TOPICS = ["iot/rpi4/accel", "iot/rpi4/temp", "iot/status/rpi4"]


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    tmp.replace(CONFIG_PATH)


def broker_from_uri(uri):
    parsed = urlparse(uri)
    return parsed.hostname or "192.168.10.1", parsed.port or 1883


class MqttThread(QtCore.QThread):
    accel = QtCore.pyqtSignal(int, str, str, int, float, float, float)
    temp = QtCore.pyqtSignal(int, str, str, int, float)
    mqtt_status = QtCore.pyqtSignal(str)

    def run(self):
        cfg = load_config()
        host, port = broker_from_uri(cfg["mqtt_broker_uri"])
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()
        client.reconnect_delay_set(1, 30)

        def on_connect(c, _u, _f, rc, *args):
            self.mqtt_status.emit(f"conectado rc={rc}")
            for topic in TOPICS:
                c.subscribe(topic, qos=2)

        def on_disconnect(_c, _u, rc, *args):
            self.mqtt_status.emit(f"desconectado rc={rc}")

        def on_message(_c, _u, msg):
            if msg.topic == "iot/status/rpi4":
                self.mqtt_status.emit(msg.payload.decode("utf-8", errors="replace"))
                return
            env = sensors_pb2.SensorEnvelope()
            try:
                env.ParseFromString(msg.payload)
            except Exception as exc:
                self.mqtt_status.emit(f"protobuf invalido en {msg.topic}: {exc}")
                return
            payload = env.WhichOneof("payload")
            if payload == "accel":
                a = env.accel
                self.accel.emit(a.timestamp_ms, env.source_id, msg.topic, msg.qos, a.ax, a.ay, a.az)
            elif payload == "temp":
                t = env.temp
                self.temp.emit(t.timestamp_ms, env.source_id, msg.topic, msg.qos, t.temperature)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.connect(host, port, keepalive=30)
        client.loop_forever(retry_first_connection=True)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tarea 2 IoT - Raspberry MQTT")
        self.resize(1100, 720)
        self.accel_samples = deque(maxlen=1000)
        self.temp_samples = deque(maxlen=30)
        self.topic_state = {
            "iot/rpi4/accel": {"qos": "-", "last": None, "count": 0},
            "iot/rpi4/temp": {"qos": "-", "last": None, "count": 0},
        }
        self.csv_file = None
        self.csv_writer = None

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.build_accel_tab(), "Acelerometro")
        tabs.addTab(self.build_temp_tab(), "Temperatura")
        tabs.addTab(self.build_status_tab(), "Estado")
        tabs.addTab(self.build_config_tab(), "Configuracion")
        tabs.addTab(self.build_csv_tab(), "CSV")
        self.setCentralWidget(tabs)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(1000)

        self.mqtt = MqttThread(self)
        self.mqtt.accel.connect(self.on_accel)
        self.mqtt.temp.connect(self.on_temp)
        self.mqtt.mqtt_status.connect(self.on_mqtt_status)
        self.mqtt.start()

    def build_accel_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.accel_plot = pg.PlotWidget(title="Acelerometro ultimos 2 s")
        self.accel_plot.addLegend()
        self.accel_curves = {
            "ax": self.accel_plot.plot(pen="r", name="Ax"),
            "ay": self.accel_plot.plot(pen="g", name="Ay"),
            "az": self.accel_plot.plot(pen="b", name="Az"),
        }
        self.accel_stats = QtWidgets.QLabel("Sin datos")
        layout.addWidget(self.accel_plot)
        layout.addWidget(self.accel_stats)
        return widget

    def build_temp_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.temp_label = QtWidgets.QLabel("Temperatura: sin datos")
        self.temp_label.setStyleSheet("font-size: 28px")
        self.temp_plot = pg.PlotWidget(title="Ultimas 30 temperaturas")
        self.temp_curve = self.temp_plot.plot(pen="y", symbol="o")
        layout.addWidget(self.temp_label)
        layout.addWidget(self.temp_plot)
        return widget

    def build_status_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.status_label = QtWidgets.QLabel("MQTT: iniciando")
        self.table = QtWidgets.QTableWidget(2, 4)
        self.table.setHorizontalHeaderLabels(["Topico", "QoS activo", "Ultimo mensaje", "Mensajes recibidos"])
        for row, topic in enumerate(("iot/rpi4/accel", "iot/rpi4/temp")):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(topic))
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        return widget

    def build_config_tab(self):
        widget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(widget)
        self.enabled = {}
        self.qos = {}
        for name, label in (("accel", "Acelerometro"), ("temp", "Temperatura")):
            row = QtWidgets.QHBoxLayout()
            self.enabled[name] = QtWidgets.QCheckBox("Activo")
            self.qos[name] = QtWidgets.QComboBox()
            self.qos[name].addItems(["0", "1", "2"])
            row.addWidget(self.enabled[name])
            row.addWidget(QtWidgets.QLabel("QoS"))
            row.addWidget(self.qos[name])
            form.addRow(label, row)
        buttons = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton("Aplicar")
        reload_btn = QtWidgets.QPushButton("Recargar")
        apply_btn.clicked.connect(self.apply_config)
        reload_btn.clicked.connect(self.reload_config)
        buttons.addWidget(apply_btn)
        buttons.addWidget(reload_btn)
        form.addRow(buttons)
        self.reload_config()
        return widget

    def build_csv_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        self.csv_button = QtWidgets.QPushButton("Iniciar guardado CSV")
        self.csv_button.clicked.connect(self.toggle_csv)
        self.csv_status = QtWidgets.QLabel(f"Archivo: {CSV_PATH}")
        layout.addWidget(self.csv_button)
        layout.addWidget(self.csv_status)
        layout.addStretch()
        return widget

    def reload_config(self):
        cfg = load_config()
        for name in ("accel", "temp"):
            self.enabled[name].setChecked(bool(cfg["sensors"][name]["enabled"]))
            self.qos[name].setCurrentText(str(cfg["sensors"][name]["qos"]))

    def apply_config(self):
        cfg = load_config()
        for name in ("accel", "temp"):
            cfg["sensors"][name]["enabled"] = self.enabled[name].isChecked()
            cfg["sensors"][name]["qos"] = int(self.qos[name].currentText())
        save_config(cfg)
        self.status_label.setText("Configuracion aplicada; publisher recargara config.json")

    def toggle_csv(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.csv_button.setText("Iniciar guardado CSV")
            self.csv_status.setText(f"Guardado detenido. Archivo: {CSV_PATH}")
            return
        new_file = not CSV_PATH.exists()
        self.csv_file = CSV_PATH.open("a", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        if new_file:
            self.csv_writer.writerow(["timestamp_ms", "source", "topic", "qos", "ax", "ay", "az", "temperature"])
        self.csv_button.setText("Detener guardado CSV")
        self.csv_status.setText(f"Guardando en {CSV_PATH}")

    def on_accel(self, ts, source, topic, qos, ax, ay, az):
        self.accel_samples.append((ts, ax, ay, az))
        self.update_topic(topic, qos)
        data = list(self.accel_samples)[-100:]
        x = np.arange(len(data)) * 0.02
        for idx, name in enumerate(("ax", "ay", "az"), start=1):
            self.accel_curves[name].setData(x, [row[idx] for row in data])
        arr = np.array([[row[1], row[2], row[3]] for row in self.accel_samples])
        rms = np.sqrt(np.mean(arr * arr, axis=0))
        peak = np.max(arr, axis=0)
        p2p = np.ptp(arr, axis=0)
        self.accel_stats.setText(
            f"RMS ax/ay/az={rms[0]:.2f}/{rms[1]:.2f}/{rms[2]:.2f} | "
            f"Peak={peak[0]:.2f}/{peak[1]:.2f}/{peak[2]:.2f} | "
            f"P-P={p2p[0]:.2f}/{p2p[1]:.2f}/{p2p[2]:.2f}"
        )
        self.write_csv([ts, source, topic, qos, f"{ax:.4f}", f"{ay:.4f}", f"{az:.4f}", ""])

    def on_temp(self, ts, source, topic, qos, temp):
        self.temp_samples.append((ts, temp))
        self.update_topic(topic, qos)
        self.temp_label.setText(f"Temperatura: {temp:.1f} C | ts={ts} ms")
        self.temp_curve.setData(np.arange(len(self.temp_samples)), [row[1] for row in self.temp_samples])
        self.write_csv([ts, source, topic, qos, "", "", "", f"{temp:.4f}"])

    def write_csv(self, row):
        if self.csv_writer:
            self.csv_writer.writerow(row)
            self.csv_file.flush()

    def update_topic(self, topic, qos):
        if topic in self.topic_state:
            self.topic_state[topic]["qos"] = qos
            self.topic_state[topic]["last"] = time.time()
            self.topic_state[topic]["count"] += 1

    def refresh_status(self):
        for row, topic in enumerate(("iot/rpi4/accel", "iot/rpi4/temp")):
            state = self.topic_state[topic]
            last = "nunca" if state["last"] is None else f"{time.time() - state['last']:.1f} s"
            for col, value in enumerate((topic, state["qos"], last, state["count"])):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(value)))

    def on_mqtt_status(self, text):
        self.status_label.setText(f"MQTT: {text}")

    def closeEvent(self, event):
        if self.csv_file:
            self.csv_file.close()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
