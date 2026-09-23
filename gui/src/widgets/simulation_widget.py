import math
import time

from PyQt6 import QtCore, QtWidgets
from src.package.Station import DEFAULT_GROUP_COUNT, STATION_ANGLES_COUNT
from src.protocol.protocol_handler import ProtocolHandler

AUTOSEND_INTERVAL_MS = 200


class SimulationWidget(QtWidgets.QWidget):
    def __init__(self, protocol: ProtocolHandler, main_window, parent=None):
        super().__init__(parent)
        self.protocol = protocol
        self.main_window = main_window
        self.group_ids = list(getattr(main_window, "group_ids", range(DEFAULT_GROUP_COUNT)))
        self.angle_count = STATION_ANGLES_COUNT
        self.station_checkboxes = []
        self.setWindowTitle("Serial data emulator")
        self.setGeometry(100, 100, 420, 320)

        self.message_le = QtWidgets.QLineEdit()
        self.format_cb = QtWidgets.QComboBox()
        self.format_cb.addItems(["ASCII", "Hex", "Binary", "Raw bytes"])
        self.format_cb.currentTextChanged.connect(self.update_placeholder)
        self.send_btn = QtWidgets.QPushButton("Send", clicked=self.send_simulated_data)
        self.auto_mode_cb = QtWidgets.QCheckBox("Autosend", toggled=self.toggle_auto_mode)

        self.group_row = QtWidgets.QHBoxLayout()
        self.output_te = QtWidgets.QTextEdit(readOnly=True)
        self.close_btn = QtWidgets.QPushButton("Close", clicked=self.close)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Message"))
        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(self.message_le)
        input_layout.addWidget(QtWidgets.QLabel("Format"))
        input_layout.addWidget(self.format_cb)
        lay.addLayout(input_layout)
        lay.addWidget(self.send_btn)
        lay.addWidget(self.auto_mode_cb)
        lay.addLayout(self.group_row)
        lay.addWidget(self.output_te)
        lay.addWidget(self.close_btn)

        self.auto_timer = QtCore.QTimer()
        self.auto_timer.setInterval(AUTOSEND_INTERVAL_MS)
        self.auto_timer.timeout.connect(self.send_auto_data)
        self.start_time = time.time()
        self._build_group_checks()
        self.update_placeholder()

    def set_groups(self, group_ids: list[int]) -> None:
        self.group_ids = list(group_ids)
        self._build_group_checks()

    def _build_group_checks(self) -> None:
        while self.group_row.count():
            item = self.group_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.station_checkboxes.clear()
        self.group_row.addWidget(QtWidgets.QLabel("Groups"))
        autosend = self.auto_mode_cb.isChecked()
        for i, gid in enumerate(self.group_ids):
            cb = QtWidgets.QCheckBox(str(gid))
            cb.setProperty("gid", gid)
            cb.setChecked(i == 0)
            cb.setEnabled(autosend)
            self.station_checkboxes.append(cb)
            self.group_row.addWidget(cb)

    @QtCore.pyqtSlot()
    def send_simulated_data(self):
        text = self.message_le.text().strip()
        if not text:
            return
        format_type = self.format_cb.currentText()
        try:
            if format_type == "ASCII":
                data = text.encode("utf-8")
            elif format_type == "Hex":
                data = bytes.fromhex(text.replace(" ", ""))
            elif format_type == "Binary":
                bin_values = []
                for b in text.split():
                    val = int(b, 2)
                    if val > 255 or val < 0:
                        raise ValueError(f"Binary value {b} is outside 0-255")
                    bin_values.append(val)
                data = bytes(bin_values)
            elif format_type == "Raw bytes":
                raw_bytes = []
                for b in text.split():
                    val = int(b)
                    if not (0 <= val <= 255):
                        raise ValueError(f"Byte {b} is outside 0-255")
                    raw_bytes.append(val)
                data = bytes(raw_bytes)
            else:
                raise ValueError("Unsupported format")
        except ValueError as e:
            self.output_te.append(f"Parse error: {e}")
            return

        self.output_te.append(f"TX {data.hex()}")
        try:
            messages = self.protocol.on_bytes(data)
            self.output_te.append(f"Parsed {len(messages)}")
            for msg in messages:
                self.main_window.processParsedMessage(msg)
        except Exception as e:
            self.output_te.append(f"Parse error: {e}")
        self.message_le.clear()

    @QtCore.pyqtSlot(bool)
    def toggle_auto_mode(self, checked):
        for cb in self.station_checkboxes:
            cb.setEnabled(checked)
        if checked:
            self.start_time = time.time()
            self.auto_timer.start()
            self.output_te.append(f"Autosend on, every {AUTOSEND_INTERVAL_MS} ms")
        else:
            self.auto_timer.stop()
            self.output_te.append("Autosend off")

    @QtCore.pyqtSlot()
    def send_auto_data(self):
        current_time = time.time() - self.start_time
        for cb in self.station_checkboxes:
            if not cb.isChecked():
                continue
            gid = int(cb.property("gid"))
            for angle_idx in range(self.angle_count):
                offset = (gid * 0.5) + (angle_idx * 0.3)
                value = int(math.sin(current_time + offset) * 90)
                self.main_window.processParsedMessage(
                    {"station_index": gid, "angle": angle_idx, "value": value}
                )

    @QtCore.pyqtSlot(str)
    def update_placeholder(self, format_type=None):
        if format_type is None:
            format_type = self.format_cb.currentText()
        placeholders = {
            "ASCII": "R-10",
            "Hex": "52 2D 31 30",
            "Binary": "01010010 00101101",
            "Raw bytes": "82 45 49 48",
        }
        self.message_le.setPlaceholderText(placeholders.get(format_type, ""))

    def closeEvent(self, event):
        self.auto_timer.stop()
        owner = self.main_window
        if owner.simulation_widget is self:
            owner.simulation_widget = None
            owner.toggleSerialConnection()
        super().closeEvent(event)
