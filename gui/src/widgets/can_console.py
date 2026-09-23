import logging
import math
import random
import time
from datetime import datetime

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.package.Station import BASE_CAN_ID, group_can_id, group_label


def frame_text(can_id: int, data: bytes) -> str:
    hex_data = " ".join(f"{b:02X}" for b in data)
    ascii_data = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    return f"TX ID=0x{can_id:03X} DLC={len(data)} {hex_data}  {ascii_data}"


def log_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class CanConsole(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.group_ids = list(main_window.group_ids)
        self.setWindowTitle("CAN console")
        self.setGeometry(100, 100, 1100, 720)

        self.message_history = []
        self.max_history = 1000
        self.paused = False
        self.filter_enabled = False
        self.filter_ids = set()
        self.auto_scroll_enabled = True
        self.rx_count = 0
        self.tx_count = 0

        self.continuous_sending = False
        self.continuous_timer = None
        self.random_active = False
        self.random_timer = None
        self.random_states = {}
        self.station_last_data = {}

        self.angle_group_checks = []
        self.random_group_checks = []
        self.random_group_modes = []
        self._live_tx = False

        self.setup_ui()
        self.set_groups(self.group_ids)

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.refresh_station_table)
        self.update_timer.start(1000)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 14, 8, 8)
        main_layout.setSpacing(8)
        top_controls_layout = QHBoxLayout()

        can_mode_group = QGroupBox("CAN mode")
        can_mode_layout = QHBoxLayout()
        self.normal_mode_btn = QPushButton("Normal")
        self.normal_mode_btn.clicked.connect(lambda: self.set_can_mode("NORMAL"))
        self.loopback_mode_btn = QPushButton("Loopback")
        self.loopback_mode_btn.clicked.connect(lambda: self.set_can_mode("LOOPBACK"))
        can_mode_layout.addWidget(self.normal_mode_btn)
        can_mode_layout.addWidget(self.loopback_mode_btn)
        can_mode_layout.setContentsMargins(8, 16, 8, 8)
        can_mode_group.setLayout(can_mode_layout)
        top_controls_layout.addWidget(can_mode_group)

        control_group = QGroupBox("Monitor")
        control_layout = QHBoxLayout()
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)

        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.toggled.connect(self.toggle_autoscroll)
        control_layout.addWidget(self.autoscroll_check)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_messages)
        control_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_log)
        control_layout.addWidget(export_btn)

        self.filter_check = QCheckBox("Filter")
        self.filter_check.toggled.connect(self.toggle_filter)
        control_layout.addWidget(self.filter_check)

        self.filter_line = QLineEdit()
        self.filter_line.setPlaceholderText("0x100, 0x101")
        self.filter_line.setMaximumWidth(160)
        self.filter_line.textChanged.connect(self.update_filter_ids)
        self.filter_line.setEnabled(False)
        control_layout.addWidget(self.filter_line)

        self.msg_counter_label = QLabel("RX 0   TX 0")
        control_layout.addWidget(self.msg_counter_label)
        control_layout.addStretch()
        control_layout.setContentsMargins(8, 16, 8, 8)
        control_group.setLayout(control_layout)
        top_controls_layout.addWidget(control_group, stretch=1)
        main_layout.addLayout(top_controls_layout)

        main_content_layout = QHBoxLayout()
        left_column = QVBoxLayout()

        station_group = QGroupBox("Groups")
        station_layout = QVBoxLayout()
        self.station_table = QTableWidget()
        self.station_table.setColumnCount(7)
        self.station_table.setHorizontalHeaderLabels(
            ["ID", "Roll", "Age", "Pitch", "Age", "Yaw", "Age"]
        )
        self.station_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.station_table.setAlternatingRowColors(True)
        self.station_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        station_layout.addWidget(self.station_table)
        station_layout.setContentsMargins(8, 16, 8, 8)
        station_group.setLayout(station_layout)
        left_column.addWidget(station_group, stretch=1)

        tx_group = QGroupBox("Send")
        tx_layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Manual", "Angle", "LED", "Random"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        tx_layout.addLayout(mode_layout)

        self.tx_stack = QtWidgets.QStackedWidget()
        self.tx_stack.addWidget(self._build_manual_page())
        self.tx_stack.addWidget(self._build_angle_page())
        self.tx_stack.addWidget(self._build_led_page())
        self.tx_stack.addWidget(self._build_random_page())
        tx_layout.addWidget(self.tx_stack)
        tx_layout.setContentsMargins(8, 16, 8, 8)
        tx_group.setLayout(tx_layout)
        left_column.addWidget(tx_group, stretch=1)
        main_content_layout.addLayout(left_column, stretch=2)

        right_column = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        right_column.setChildrenCollapsible(False)
        right_column.setHandleWidth(6)
        rx_group = QGroupBox("Received")
        rx_layout = QVBoxLayout()
        self.rx_table = QTableWidget()
        self.rx_table.setColumnCount(6)
        self.rx_table.setHorizontalHeaderLabels(["Time", "ID", "DLC", "Type", "Hex", "ASCII"])
        self.rx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.rx_table.horizontalHeader().setStretchLastSection(True)
        self.rx_table.setAlternatingRowColors(True)
        self.rx_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rx_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        rx_layout.addWidget(self.rx_table)
        rx_layout.setContentsMargins(8, 16, 8, 8)
        rx_group.setLayout(rx_layout)
        right_column.addWidget(rx_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtGui.QFont("Courier New", 9))
        log_layout.addWidget(self.log_text)
        log_layout.setContentsMargins(8, 16, 8, 8)
        log_group.setLayout(log_layout)
        right_column.addWidget(log_group)
        right_column.setStretchFactor(0, 3)
        right_column.setStretchFactor(1, 2)
        main_content_layout.addWidget(right_column, stretch=3)
        main_layout.addLayout(main_content_layout)

    def _build_manual_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID"))
        self.manual_id_line = QLineEdit("0x100")
        self.manual_id_line.setMaximumWidth(100)
        id_layout.addWidget(self.manual_id_line)
        id_layout.addStretch()
        layout.addLayout(id_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format"))
        self.manual_format_hex = QRadioButton("Hex")
        self.manual_format_ascii = QRadioButton("ASCII")
        self.manual_format_hex.setChecked(True)
        self.manual_format_hex.toggled.connect(self.on_manual_format_changed)
        format_layout.addWidget(self.manual_format_hex)
        format_layout.addWidget(self.manual_format_ascii)
        format_layout.addStretch()
        layout.addLayout(format_layout)

        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("Data"))
        self.manual_data_line = QLineEdit()
        self.manual_data_line.setPlaceholderText("52 2D 31 30")
        data_layout.addWidget(self.manual_data_line)
        layout.addLayout(data_layout)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_manual_message)
        layout.addWidget(send_btn)
        return page

    def _build_angle_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QHBoxLayout()
        form.addWidget(QLabel("Type"))
        self.angle_type_combo = QComboBox()
        self.angle_type_combo.addItem("Roll", "R")
        self.angle_type_combo.addItem("Pitch", "C")
        self.angle_type_combo.addItem("Yaw", "O")
        form.addWidget(self.angle_type_combo)
        form.addWidget(QLabel("Value"))
        self.angle_value_spin = QSpinBox()
        self.angle_value_spin.setRange(-179, 180)
        form.addWidget(self.angle_value_spin)
        form.addStretch()
        layout.addLayout(form)

        self.angle_group_layout = QHBoxLayout()
        self.angle_group_layout.addWidget(QLabel("Groups"))
        all_btn = QPushButton("All")
        all_btn.setMaximumWidth(48)
        all_btn.clicked.connect(lambda: self._set_checks(self.angle_group_checks, True))
        none_btn = QPushButton("None")
        none_btn.setMaximumWidth(48)
        none_btn.clicked.connect(lambda: self._set_checks(self.angle_group_checks, False))
        self.angle_group_layout.addWidget(all_btn)
        self.angle_group_layout.addWidget(none_btn)
        self.angle_group_layout.addStretch()
        layout.addLayout(self.angle_group_layout)

        continuous = QHBoxLayout()
        self.continuous_check = QCheckBox("Repeat")
        continuous.addWidget(self.continuous_check)
        continuous.addWidget(QLabel("Period (ms)"))
        self.continuous_period_spin = QSpinBox()
        self.continuous_period_spin.setRange(50, 5000)
        self.continuous_period_spin.setValue(200)
        self.continuous_period_spin.setSingleStep(50)
        continuous.addWidget(self.continuous_period_spin)
        continuous.addStretch()
        layout.addLayout(continuous)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_angle_message)
        layout.addWidget(send_btn)
        return page

    def _build_led_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QHBoxLayout()
        form.addWidget(QLabel("Group"))
        self.led_group_combo = QComboBox()
        form.addWidget(self.led_group_combo)
        self.led_r_check = QCheckBox("R")
        self.led_g_check = QCheckBox("G")
        self.led_b_check = QCheckBox("B")
        form.addWidget(self.led_r_check)
        form.addWidget(self.led_g_check)
        form.addWidget(self.led_b_check)
        form.addStretch()
        layout.addLayout(form)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_led_command)
        layout.addWidget(send_btn)
        return page

    def _build_random_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.random_group_layout = QHBoxLayout()
        self.random_group_layout.addWidget(QLabel("Groups"))
        all_btn = QPushButton("All")
        all_btn.setMaximumWidth(48)
        all_btn.clicked.connect(lambda: self._set_checks(self.random_group_checks, True))
        none_btn = QPushButton("None")
        none_btn.setMaximumWidth(48)
        none_btn.clicked.connect(lambda: self._set_checks(self.random_group_checks, False))
        self.random_group_layout.addWidget(all_btn)
        self.random_group_layout.addWidget(none_btn)
        self.random_group_layout.addStretch()
        layout.addLayout(self.random_group_layout)

        mode_box = QGroupBox("Signal")
        self.mode_grid = QHBoxLayout()
        mode_box.setLayout(self.mode_grid)
        layout.addWidget(mode_box)

        control = QHBoxLayout()
        control.addWidget(QLabel("Period (ms)"))
        self.random_period_spin = QSpinBox()
        self.random_period_spin.setRange(50, 5000)
        self.random_period_spin.setValue(200)
        self.random_period_spin.setSingleStep(50)
        control.addWidget(self.random_period_spin)
        self.random_toggle_btn = QPushButton("Start")
        self.random_toggle_btn.setCheckable(True)
        self.random_toggle_btn.toggled.connect(self.toggle_random_traffic)
        control.addWidget(self.random_toggle_btn)
        control.addStretch()
        layout.addLayout(control)
        return page

    def set_groups(self, group_ids: list[int]) -> None:
        if self.random_active:
            self.random_toggle_btn.setChecked(False)
        if self.continuous_sending:
            self.stop_continuous_sending()
        self.group_ids = list(group_ids)
        self._fill_led_groups()
        self._ensure_station_data()
        self._rebuild_station_table()
        self._replace_checks(self.angle_group_layout, self.angle_group_checks)
        self._replace_checks(self.random_group_layout, self.random_group_checks)
        self._rebuild_modes()

    def _fill_led_groups(self) -> None:
        current = self.led_group_combo.currentData()
        self.led_group_combo.clear()
        for gid in self.group_ids:
            self.led_group_combo.addItem(str(gid), gid)
        index = self.led_group_combo.findData(current)
        if index >= 0:
            self.led_group_combo.setCurrentIndex(index)

    def _blank_station(self):
        return {
            "R": {"value": None, "time": None},
            "C": {"value": None, "time": None},
            "O": {"value": None, "time": None},
        }

    def _ensure_station_data(self):
        for gid in self.group_ids:
            if gid not in self.station_last_data:
                self.station_last_data[gid] = self._blank_station()
        for gid in list(self.station_last_data):
            if gid not in self.group_ids:
                del self.station_last_data[gid]

    def _rebuild_station_table(self):
        self.station_table.setRowCount(len(self.group_ids))
        for row, gid in enumerate(self.group_ids):
            self.station_table.setItem(row, 0, QTableWidgetItem(group_label(gid)))
        self.refresh_station_table()

    def _replace_checks(self, layout: QHBoxLayout, checks: list) -> None:
        for cb in checks:
            layout.removeWidget(cb)
            cb.setParent(None)
            cb.deleteLater()
        checks.clear()
        for i, gid in enumerate(self.group_ids):
            cb = QCheckBox(str(gid))
            cb.setProperty("gid", gid)
            cb.setChecked(i == 0)
            checks.append(cb)
            layout.insertWidget(1 + i, cb)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child = item.layout()
            widget = item.widget()
            if child is not None:
                self._clear_layout(child)
            if widget is not None:
                widget.deleteLater()

    def _rebuild_modes(self) -> None:
        self._clear_layout(self.mode_grid)
        self.random_group_modes.clear()
        for gid in self.group_ids:
            mode_combo = QComboBox()
            mode_combo.addItems(["Sine", "Const", "Noise"])
            mode_combo.setMaximumWidth(72)
            self.random_group_modes.append(mode_combo)
            column = QVBoxLayout()
            column.addWidget(QLabel(str(gid)))
            column.addWidget(mode_combo)
            self.mode_grid.addLayout(column)

    def _set_checks(self, checks, checked: bool) -> None:
        for cb in checks:
            cb.setChecked(checked)

    def set_can_mode(self, mode):
        if not self.main_window.serialConnected:
            self._log("Not connected")
            return
        try:
            self.main_window.serial.write(f"MODE_{mode}\n".encode())
            self._note_tx(f"TX MODE_{mode}")
        except Exception as e:
            self._log(f"CAN mode error: {e}")

    def toggle_pause(self, checked):
        self.paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")

    def toggle_autoscroll(self, checked):
        self.auto_scroll_enabled = checked

    def clear_messages(self):
        self.rx_table.setRowCount(0)
        self.message_history.clear()
        self.log_text.clear()
        self._live_tx = False
        self.rx_count = 0
        self.tx_count = 0
        self.update_counter_label()

    def export_log(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export log", "can_log.txt", "Text files (*.txt);;All files (*)"
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for msg in self.message_history:
                    f.write(f"{msg}\n")
            self._log(f"Exported {len(self.message_history)} lines to {filename}")
        except Exception as e:
            self._log(f"Export failed: {e}")

    def toggle_filter(self, checked):
        self.filter_enabled = checked
        self.filter_line.setEnabled(checked)

    def update_filter_ids(self, text):
        self.filter_ids.clear()
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                can_id = int(part, 16) if part.lower().startswith("0x") else int(part)
                self.filter_ids.add(can_id)
            except ValueError:
                pass

    def on_mode_changed(self, index):
        self.tx_stack.setCurrentIndex(index)

    def on_manual_format_changed(self):
        if self.manual_format_hex.isChecked():
            self.manual_data_line.setPlaceholderText("52 2D 31 30")
        else:
            self.manual_data_line.setPlaceholderText("R-10")

    def update_counter_label(self):
        self.msg_counter_label.setText(f"RX {self.rx_count}   TX {self.tx_count}")

    def on_can_message_received(self, msg):
        can_id = msg["can_id"]
        data = msg["data"]
        type_str = {"angle": "Angle", "led": "LED", "unknown": "Unknown"}.get(
            msg["type"], "Unknown"
        )

        if self.paused or (self.filter_enabled and can_id not in self.filter_ids):
            return

        timestamp = log_timestamp()
        hex_data = " ".join(f"{b:02X}" for b in data)
        ascii_data = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
        if type_str == "LED" and len(data) == 1:
            binary = f"{data[0]:08b}"
            ascii_data = f"{binary[0]} {binary[1:4]} {binary[4]} {binary[5:8]}"

        entry = (
            f"[{timestamp}] ID=0x{can_id:03X} DLC={len(data)} "
            f"Type={type_str} Hex=[{hex_data}] ASCII=[{ascii_data}]"
        )
        self.message_history.append(entry)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
            if self.rx_table.rowCount() > 0:
                self.rx_table.removeRow(0)

        self.rx_count += 1
        self.update_counter_label()

        row = self.rx_table.rowCount()
        self.rx_table.insertRow(row)
        values = [timestamp, f"0x{can_id:03X}", str(len(data)), type_str, hex_data, ascii_data]
        for col, value in enumerate(values):
            self.rx_table.setItem(row, col, QTableWidgetItem(value))
        if self.auto_scroll_enabled:
            self.rx_table.scrollToBottom()
        self.update_station_data(can_id, ascii_data)

    def update_station_data(self, can_id, ascii_data):
        group = can_id - BASE_CAN_ID
        if group not in self.group_ids:
            return
        if len(ascii_data) < 2 or ascii_data[0] not in "RCO":
            return
        try:
            angle_value = int(ascii_data[1:])
        except ValueError:
            return
        self.station_last_data[group][ascii_data[0]] = {
            "value": angle_value,
            "time": time.time(),
        }
        self.refresh_station_table()

    def refresh_station_table(self):
        now = time.time()
        for row, gid in enumerate(self.group_ids):
            data = self.station_last_data.get(gid)
            if data is None:
                continue
            for idx, angle in enumerate(["R", "C", "O"]):
                value_col = 1 + idx * 2
                time_col = 2 + idx * 2
                sample = data[angle]
                if sample["value"] is None:
                    value_text = "--"
                    time_text = "--"
                else:
                    value_text = f"{sample['value']}°"
                    time_text = self.format_elapsed_time(now - sample["time"])
                self.station_table.setItem(row, value_col, QTableWidgetItem(value_text))
                self.station_table.setItem(row, time_col, QTableWidgetItem(time_text))

    def format_elapsed_time(self, seconds):
        if seconds < 1:
            return "now"
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        return f"{int(seconds / 3600)}h"

    def send_manual_message(self):
        try:
            can_id_text = self.manual_id_line.text().strip()
            can_id = (
                int(can_id_text, 16) if can_id_text.lower().startswith("0x") else int(can_id_text)
            )
            data_text = self.manual_data_line.text().strip()
            if self.manual_format_hex.isChecked():
                data = bytes.fromhex(data_text.replace(" ", ""))
            else:
                data = data_text.encode("ascii")
            self._send_can_message(can_id, data)
        except Exception as e:
            self._log(f"Manual send error: {e}")

    def send_angle_message(self):
        if self.continuous_check.isChecked():
            if self.continuous_sending:
                self.stop_continuous_sending()
            else:
                self.start_continuous_sending()
        else:
            self._send_single_angle()

    def _selected_groups(self, checks):
        return [int(cb.property("gid")) for cb in checks if cb.isChecked()]

    def _send_single_angle(self, quiet=False):
        try:
            angle_type = self.angle_type_combo.currentData()
            value = self.angle_value_spin.value()
            selected = self._selected_groups(self.angle_group_checks)
            if not selected:
                if not quiet:
                    self._log("No groups selected")
                return
            for group in selected:
                data = f"{angle_type}{value:+d}".encode("ascii")
                self._send_can_message(group_can_id(group), data, to_log=not quiet)
        except Exception as e:
            self._log(f"Angle send error: {e}")

    def start_continuous_sending(self):
        self.continuous_sending = True
        period = self.continuous_period_spin.value()
        self.continuous_timer = QtCore.QTimer()
        self.continuous_timer.timeout.connect(lambda: self._send_single_angle(quiet=True))
        self.continuous_timer.start(period)
        self._log(f"Repeat started ({period} ms)")

    def stop_continuous_sending(self):
        if not self.continuous_sending:
            return
        self.continuous_sending = False
        if self.continuous_timer:
            self.continuous_timer.stop()
            self.continuous_timer = None
        self._log("Repeat stopped")

    def send_led_command(self):
        try:
            group = self.led_group_combo.currentData()
            if group is None:
                self._log("No group selected")
                return
            r = int(self.led_r_check.isChecked())
            g = int(self.led_g_check.isChecked())
            b = int(self.led_b_check.isChecked())
            message = self.main_window.protocol.build_led_command(group, r, g, b)
            self.main_window.serial.write(message)
            self.tx_count += 1
            self.update_counter_label()
            self.note_led(group, r, g, b)
        except NotImplementedError:
            self._log("LED command is not implemented")
        except Exception as e:
            self._log(f"LED send error: {e}")

    def toggle_random_traffic(self, checked):
        if checked:
            self.start_random_traffic()
        else:
            self.stop_random_traffic()

    def start_random_traffic(self):
        self.random_active = True
        period = self.random_period_spin.value()
        self.random_states.clear()
        for cb, mode_combo in zip(self.random_group_checks, self.random_group_modes):
            if not cb.isChecked():
                continue
            gid = int(cb.property("gid"))
            self.random_states[gid] = {
                "mode": mode_combo.currentText(),
                "start_time": time.time(),
                "const_value": random.randint(-90, 90),
                "sine_params": {
                    angle: {
                        "amp": random.randint(50, 120),
                        "period": random.uniform(5, 15),
                        "phase": random.uniform(0, 2 * math.pi),
                        "offset": random.randint(-50, 50),
                    }
                    for angle in ("R", "C", "O")
                },
            }
        if not self.random_states:
            self.random_active = False
            self.random_toggle_btn.blockSignals(True)
            self.random_toggle_btn.setChecked(False)
            self.random_toggle_btn.blockSignals(False)
            self._log("No groups selected")
            return
        self.random_timer = QtCore.QTimer()
        self.random_timer.timeout.connect(self.send_random_traffic)
        self.random_timer.start(period)
        self.random_toggle_btn.setText("Stop")
        self._log(f"Random started ({period} ms)")

    def stop_random_traffic(self):
        if not self.random_active and self.random_timer is None:
            return
        self.random_active = False
        if self.random_timer:
            self.random_timer.stop()
            self.random_timer = None
        self.random_states.clear()
        self.random_toggle_btn.setText("Start")
        self._log("Random stopped")

    def send_random_traffic(self):
        for group_id, state in self.random_states.items():
            angle_type = random.choice(("R", "C", "O"))
            mode = state["mode"]
            if mode == "Sine":
                elapsed = time.time() - state["start_time"]
                params = state["sine_params"][angle_type]
                value = params["amp"] * math.sin(
                    2 * math.pi * elapsed / params["period"] + params["phase"]
                )
                value = int(value + params["offset"] + random.uniform(-2, 2))
            elif mode == "Const":
                value = state["const_value"]
            else:
                value = random.randint(-179, 180)
            value = max(-179, min(180, value))
            try:
                self._send_can_message(
                    group_can_id(group_id),
                    f"{angle_type}{value:+d}".encode("ascii"),
                    to_log=False,
                )
            except Exception as e:
                logging.warning(f"Random traffic error: {e}")
                self._log(f"Random error group {group_id}: {e}")

    def note_led(self, group: int, r: bool, g: bool, b: bool) -> None:
        ri, gi, bi = int(r), int(g), int(b)
        payload = 0x80 | ((group << 4) & 0x70) | ((ri << 2) & 0x04) | ((gi << 1) & 0x02) | (bi & 1)
        self._note_tx(f"TX LED_{group}_{ri}_{gi}_{bi}  data={payload:02X}")

    def _log(self, text: str) -> None:
        self._live_tx = False
        self.log_text.append(f"{log_timestamp()}  {text}")

    def _note_tx(self, text: str, *, to_log: bool = True) -> None:
        line = f"{log_timestamp()}  {text}"
        if to_log or not self._live_tx:
            self._live_tx = not to_log
            self.log_text.append(line)
            return
        cursor = QtGui.QTextCursor(self.log_text.document().lastBlock())
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfBlock,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(line)
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def _send_can_message(self, can_id, data, to_log: bool = True):
        if not self.main_window.serialConnected:
            raise Exception("Not connected")
        cmd = f"SEND_{can_id:x}"
        for byte in data:
            cmd += f"_{byte:02x}"
        cmd += "\n"
        self.main_window.serial.write(cmd.encode("utf-8"))
        self.tx_count += 1
        self.update_counter_label()
        self._note_tx(frame_text(can_id, data), to_log=to_log)
        logging.debug(f"[Console] Sent: {cmd.strip()}")

    def closeEvent(self, event):
        if self.main_window.serialConnected and self.main_window.serial.is_open:
            try:
                self.main_window.serial.write(b"MODE_NORMAL\n")
                self.main_window.serial.write(b"M1\n")
                logging.info("[Console] Sent reset on close")
            except Exception as e:
                logging.warning(f"[Console] Failed to send reset on close: {e}")
        self.stop_continuous_sending()
        self.stop_random_traffic()
        self.update_timer.stop()
        event.accept()
