import logging
import time

import serial
from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QCheckBox, QLabel, QMainWindow, QMessageBox
from serial.serialutil import SerialException
from serial.tools.list_ports import comports
from src.package.Station import (
    DEFAULT_GROUP_COUNT,
    MAX_GROUP_COUNT,
    Station,
    group_id_bytes,
    group_label,
)
from src.protocol.protocol_handler import ProtocolHandler
from src.themes import DARK_THEME, LIGHT_THEME
from src.ui.mainwindow import Ui_MainWindow
from src.widgets.plot_widget import PlotWidget
from src.widgets.simulation_widget import SimulationWidget
from src.widgets.station_info_widget import StationInfoWidget

IDLE_TIMER_MS = 2500
RX_TIMER_MS = 10
LAST_TIME_UPDATE_MS = 1000
SIMULATION_NAME = "Serial data emulator"
HISTORY_LIMIT = 50
PLOT_UPDATE_MS = 100
SETTINGS_ORG = "ITBA"
SETTINGS_APP = "TiltNetworkTool"


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.COM_gb.setTitle("Serial")
        self.LED_gb.setTitle("LED")
        self.label.setText("Group")

        self.serialConnected = False
        self.connection_but.clicked.connect(self.toggleSerialConnection)

        self.actionRefresh_ports.triggered.connect(self.updateAvailablePorts)
        self.updateAvailablePorts()
        self.serial = serial.Serial()
        self.protocol = ProtocolHandler()
        self.simulation_widget = None
        self.can_console = None

        self.group_ids = self._stored_group_ids()
        self.oglw.set_group_count(len(self.group_ids))

        self.groups_label = QLabel("Groups")
        self.horizontalLayout_2.addWidget(self.groups_label)
        self.group_checks = []
        for gid in range(MAX_GROUP_COUNT):
            cb = QCheckBox(str(gid))
            cb.setChecked(gid in self.group_ids)
            self.group_checks.append(cb)
            self.horizontalLayout_2.addWidget(cb)
            cb.toggled.connect(self._on_group_toggled)

        self.stationInfoWidgets = []
        self.angle_histories = []
        self.plot_widgets = []
        self.led_states = []
        self.last_update_times = []
        self.stations = []
        self.timers = []
        for gid in self.group_ids:
            self._add_group(gid)
        self._fill_group_selector()

        self.actionFRDM_K64F.triggered.connect(self.selectFRDMModel)
        self.actionPlane.triggered.connect(self.selectPlaneModel)
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionToggle_theme.triggered.connect(self.toggleTheme)
        self.current_theme = "light"

        timer = QTimer()
        timer.setInterval(RX_TIMER_MS)
        timer.timeout.connect(self.receive)
        timer.start()
        self.rxTimer = timer

        update_timer = QTimer()
        update_timer.setInterval(LAST_TIME_UPDATE_MS)
        update_timer.timeout.connect(self.updateLastUpdateLabels)
        update_timer.start()
        self.lastUpdateTimer = update_timer

        plot_update_timer = QTimer()
        plot_update_timer.setInterval(PLOT_UPDATE_MS)
        plot_update_timer.timeout.connect(self.updateOpenPlots)
        plot_update_timer.start()
        self.plotUpdateTimer = plot_update_timer

        self.send_pb.clicked.connect(self.sendLEDCommand)
        self.led_status = QLabel("")
        self.horizontalLayout.addWidget(self.led_status)
        self.LED_gb.setEnabled(False)
        self.actionCAN_console.triggered.connect(self.open_can_console)

    def _stored_group_ids(self) -> list[int]:
        raw = QSettings(SETTINGS_ORG, SETTINGS_APP).value("groups")
        if raw:
            parts = str(raw).replace(";", ",").split(",")
            ids = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                try:
                    gid = int(part)
                except ValueError:
                    continue
                if 0 <= gid < MAX_GROUP_COUNT and gid not in ids:
                    ids.append(gid)
            if ids:
                return ids
        return list(range(DEFAULT_GROUP_COUNT))

    def _save_group_ids(self) -> None:
        text = ",".join(str(gid) for gid in self.group_ids)
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("groups", text)

    def _add_group(self, group_id: int) -> None:
        slot = len(self.stationInfoWidgets)
        siw = StationInfoWidget(self)
        siw.setEnabled(False)
        siw.setName(group_label(group_id))
        siw.plotButton.clicked.connect(self._toggle_plot(slot, group_id))
        self.stationInfoLayout.addWidget(siw)
        self.stationInfoWidgets.append(siw)
        self.angle_histories.append([[], [], []])
        self.plot_widgets.append(None)
        self.led_states.append({"r": False, "g": False, "b": False})
        self.last_update_times.append(None)
        self.stations.append(Station(id=group_id_bytes(group_id)))

        timer = QTimer()
        timer.setInterval(IDLE_TIMER_MS)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda idx=slot: self._disable_group(idx))
        timer.start()
        self.timers.append(timer)

    def _clear_groups(self) -> None:
        for plot in self.plot_widgets:
            if plot is not None:
                plot.close()
        for widget in self.stationInfoWidgets:
            self.stationInfoLayout.removeWidget(widget)
            widget.deleteLater()
        for timer in self.timers:
            timer.stop()
        self.stationInfoWidgets.clear()
        self.angle_histories.clear()
        self.plot_widgets.clear()
        self.led_states.clear()
        self.last_update_times.clear()
        self.stations.clear()
        self.timers.clear()

    def _fill_group_selector(self) -> None:
        current = self.stationSelector_cb.currentData()
        self.stationSelector_cb.blockSignals(True)
        self.stationSelector_cb.clear()
        for gid in self.group_ids:
            self.stationSelector_cb.addItem(group_label(gid), gid)
        index = self.stationSelector_cb.findData(current)
        if index >= 0:
            self.stationSelector_cb.setCurrentIndex(index)
        self.stationSelector_cb.blockSignals(False)

    def _on_group_toggled(self, _checked: bool) -> None:
        ids = [i for i, cb in enumerate(self.group_checks) if cb.isChecked()]
        if not ids:
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.blockSignals(True)
                sender.setChecked(True)
                sender.blockSignals(False)
            return
        if ids == self.group_ids:
            return
        self._clear_groups()
        self.group_ids = ids
        for gid in ids:
            self._add_group(gid)
        self.oglw.set_group_count(len(ids))
        self._fill_group_selector()
        if self.can_console is not None:
            self.can_console.set_groups(ids)
        if self.simulation_widget is not None:
            self.simulation_widget.set_groups(ids)
        self._save_group_ids()

    def _disable_group(self, station_index: int) -> None:
        if station_index >= len(self.stationInfoWidgets):
            return
        self.stationInfoWidgets[station_index].setEnabled(False)
        self.oglw.setStationInactive(station_index)

    def _toggle_plot(self, slot: int, group_id: int):
        def toggle():
            if slot >= len(self.plot_widgets):
                return
            if self.plot_widgets[slot] is None:
                self.plot_widgets[slot] = PlotWidget(group_id, self.angle_histories[slot])
                self.plot_widgets[slot].show()
            else:
                self.plot_widgets[slot].close()
                self.plot_widgets[slot] = None

        return toggle

    def updateOpenPlots(self):
        for i, plot in enumerate(self.plot_widgets):
            if plot:
                plot.updatePlot(self.angle_histories[i])

    def processParsedMessage(self, msg: dict):
        """Apply one angle sample. Keys: station_index, angle (0 roll, 1 pitch, 2 yaw), value."""
        try:
            station_index = int(msg.get("station_index"))
            angle_id = msg.get("angle")
            value = msg.get("value")
        except Exception as e:
            logging.warning(f"[MainWindow] Invalid message: {msg} ({e})")
            return

        angle_index = self._resolve_angle_index(angle_id)
        if angle_index not in (0, 1, 2):
            logging.warning(f"[MainWindow] Unknown angle: {angle_id}")
            return

        try:
            slot = self.group_ids.index(station_index)
        except ValueError:
            return

        if self.stations[slot].assignAngle(angle_index, value):
            current_time = time.time()
            history = self.angle_histories[slot][angle_index]
            history.append((current_time, value))
            if len(history) > HISTORY_LIMIT:
                history.pop(0)

            self.last_update_times[slot] = current_time
            self.timers[slot].start()
            self.stationInfoWidgets[slot].setEnabled(True)
            self.stationInfoWidgets[slot].setAngleLabels(self.stations[slot].angles)
            self.oglw.setOrientation(
                slot,
                -self.stations[slot].roll,
                -self.stations[slot].pitch,
                +self.stations[slot].yaw + 90,
            )

    def _resolve_angle_index(self, angle_id):
        if isinstance(angle_id, int) and angle_id in (0, 1, 2):
            return angle_id
        return -1

    def receive(self):
        if not self.serialConnected or not self.serial.is_open:
            return
        try:
            while self.serial.in_waiting > 0:
                to_read = self.serial.in_waiting or 1
                chunk = self.serial.read(to_read)
                try:
                    messages = self.protocol.on_bytes(chunk)
                except NotImplementedError as e:
                    logging.warning(
                        f"[MainWindow] ProtocolHandler.on_bytes is not implemented: {e}"
                    )
                    break

                if not messages:
                    continue
                for msg in messages:
                    if self.can_console and self.can_console.isVisible():
                        self.can_console.on_can_message_received(msg)

                    if msg["type"] == "angle":
                        self.processParsedMessage(msg)
                    elif msg["type"] == "led":
                        station_index = msg["station_index"]
                        if station_index not in self.group_ids:
                            continue
                        slot = self.group_ids.index(station_index)
                        self.led_states[slot] = {
                            "r": msg["r"],
                            "g": msg["g"],
                            "b": msg["b"],
                        }
                        self.stationInfoWidgets[slot].update_led(msg["r"], msg["g"], msg["b"])

        except (SerialException, OSError) as e:
            logging.error(f"[MainWindow] Error reading from serial port: {e}")

    def toggleSerialConnection(self):
        if not self.serialConnected:
            self.port = self.getPort()
            port = self.port
            if port == SIMULATION_NAME:
                self.serialConnected = True
                self.simulation_widget = SimulationWidget(self.protocol, self)
                self.simulation_widget.show()
            elif port:
                try:
                    self.serial.baudrate = int(self.baudrate_cb.currentText())
                    self.serial.port = port
                    self.serial.open()
                    if self.serial.is_open:
                        self.serialConnected = True
                        logging.info(f"[MainWindow] Connected to serial port: {port}")
                    else:
                        raise SerialException("Failed to open port")
                except (SerialException, ValueError, OSError) as e:
                    logging.error(f"[MainWindow] Failed to connect to serial port {port}: {e}")
                    QMessageBox.warning(
                        self, "Connection error", f"Could not connect to {port}.\n{e}"
                    )
                    self.serialConnected = False
            else:
                QMessageBox.warning(self, "No port", "Select a serial port.")
                self.serialConnected = False
        else:
            try:
                if self.simulation_widget:
                    widget = self.simulation_widget
                    self.simulation_widget = None
                    widget.close()
                if self.serial.is_open:
                    try:
                        self.serial.write(b"M1\n")
                        logging.info("[MainWindow] Sent M1 on disconnect")
                    except Exception as e:
                        logging.warning(f"[MainWindow] Failed to send M1 on disconnect: {e}")

                    self.serial.close()
                    logging.info("[MainWindow] Disconnected")
            except SerialException as e:
                logging.warning(f"[MainWindow] Error closing serial port: {e}")
            self.serialConnected = False
            n = len(self.group_ids)
            self.angle_histories = [[[], [], []] for _ in range(n)]
            self.led_states = [{"r": False, "g": False, "b": False} for _ in range(n)]
            for siw in self.stationInfoWidgets:
                siw.update_led(False, False, False)

        self.configPortSettings(self.serialConnected)

    def configPortSettings(self, connected=False):
        self.COM_gb.setEnabled(not connected)
        self.LED_gb.setEnabled(connected)
        if not connected:
            self.led_status.setText("")
        self.connection_but.setText("Disconnect" if connected else "Connect")

    def updateAvailablePorts(self):
        self.port_cb.clear()
        for port, desc, _hwid in comports():
            self.port_cb.addItem(f"{port} - {desc}")
        self.port_cb.addItem(SIMULATION_NAME)

    def getPort(self):
        text = self.port_cb.currentText()
        if text:
            return text.split(" - ")[0]
        return None

    def selectFRDMModel(self):
        if self.actionFRDM_K64F.isChecked():
            self.actionPlane.setChecked(False)
            self.oglw.setModelIndex(0)
        else:
            self.actionPlane.setChecked(True)
            self.selectPlaneModel()

    def selectPlaneModel(self):
        if self.actionPlane.isChecked():
            self.actionFRDM_K64F.setChecked(False)
            self.oglw.setModelIndex(1)
        else:
            self.actionFRDM_K64F.setChecked(True)
            self.selectFRDMModel()

    def sendLEDCommand(self):
        if (self.port != SIMULATION_NAME) and (not self.serialConnected or not self.serial.is_open):
            QMessageBox.warning(self, "Not connected", "Connect to a serial port first.")
            return

        group_id = self.stationSelector_cb.currentData()
        if group_id is None:
            return
        self.selected_station_index = group_id
        self.selected_r = self.r_checkb.isChecked()
        self.selected_g = self.g_checkb.isChecked()
        self.selected_b = self.b_checkb.isChecked()

        try:
            message = self.protocol.build_led_command(
                group_id, self.selected_r, self.selected_g, self.selected_b
            )
        except NotImplementedError as e:
            logging.warning(f"[MainWindow] build_led_command is not implemented: {e}")
            return
        except Exception as e:
            logging.error(f"[MainWindow] Error building LED command: {e}")
            QMessageBox.warning(self, "Command error", f"Failed to build LED command: {e}")
            return

        if not message:
            logging.warning("[MainWindow] build_led_command returned nothing.")
            QMessageBox.information(self, "No command", "Nothing to send.")
            return

        try:
            self.serial.write(message)
            logging.debug(f"[MainWindow] Sent {len(message)} bytes: {message}")
            channels = "".join(
                name
                for name, on in (
                    ("R", self.selected_r),
                    ("G", self.selected_g),
                    ("B", self.selected_b),
                )
                if on
            )
            self.led_status.setText(f"Sent {group_label(group_id)} {channels or 'off'}")
            if self.can_console is not None and self.can_console.isVisible():
                self.can_console.note_led(
                    group_id, self.selected_r, self.selected_g, self.selected_b
                )
        except (SerialException, OSError) as e:
            logging.error(f"[MainWindow] Send error: {e}")
            QMessageBox.warning(self, "Send error", f"Failed to send command: {e}")

    def showAbout(self):
        about_text = """
        <h2>Tilt Network Tool</h2>
        <p>Monitor for a CAN tilt network.</p>
        <p>Support tool for 25.27 Embedded Systems at ITBA.
        FRDM-K64F stations report roll, pitch, and yaw on a shared CAN bus.</p>
        <p><b>Credits</b></p>
        <ul>
            <li>Juan Francisco Sbruzzi (original TiltNetworkTool)</li>
            <li>Alejandro Nahuel Heir</li>
        </ul>
        <p><b>Source</b>
        <a href="https://github.com/alheir/TiltNetworkTool">github.com/alheir/TiltNetworkTool</a></p>
        """
        QMessageBox.about(self, "About", about_text)

    def updateLastUpdateLabels(self):
        current_time = time.time()
        for i, last_time in enumerate(self.last_update_times):
            if last_time is not None:
                self.stationInfoWidgets[i].setLastUpdateTime(current_time - last_time)
            else:
                self.stationInfoWidgets[i].setLastUpdateTime(None)

    def closeEvent(self, event):
        if (
            self.can_console
            and self.can_console.isVisible()
            and self.serialConnected
            and self.serial.is_open
        ):
            try:
                self.serial.write(b"MODE_NORMAL\n")
                self.serial.write(b"M1\n")
                logging.info("[MainWindow] Sent reset on close")
            except Exception as e:
                logging.warning(f"[MainWindow] Failed to send reset on close: {e}")

        if self.simulation_widget:
            widget = self.simulation_widget
            self.simulation_widget = None
            widget.close()
        if self.can_console:
            self.can_console.close()

        try:
            if self.serial.is_open:
                self.serial.close()
        except SerialException as e:
            logging.warning(f"[MainWindow] Error closing serial on exit: {e}")
        event.accept()

    def setTheme(self, theme):
        self.current_theme = theme
        self.oglw.setTheme(theme)

    def toggleTheme(self):
        if self.current_theme == "light":
            self.app.setStyleSheet(DARK_THEME)
            self.current_theme = "dark"
        else:
            self.app.setStyleSheet(LIGHT_THEME)
            self.current_theme = "light"
        self.setTheme(self.current_theme)

    def open_can_console(self):
        if not self.serialConnected or self.port == SIMULATION_NAME:
            QMessageBox.warning(
                self,
                "Connection required",
                "Connect to a serial port to open the CAN console.",
            )
            return
        if self.can_console is None:
            from src.widgets.can_console import CanConsole

            self.can_console = CanConsole(self)
        self.can_console.show()
        self.can_console.raise_()
        self.can_console.activateWindow()

        try:
            self.serial.write(b"M1\n")
            logging.info("[MainWindow] Sent M1 on CAN console open")
        except Exception as e:
            logging.warning(f"[MainWindow] Failed to send M1 on CAN console open: {e}")
