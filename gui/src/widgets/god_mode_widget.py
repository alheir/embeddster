from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QLineEdit, QComboBox, QCheckBox, QGroupBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QRadioButton)
from datetime import datetime
import logging
import time
import math
import random
from src.package.Station import STATION_COUNT

class GodModeWidget(QWidget):
    """
    Advanced widget for CAN monitoring and message injection.
    Acts as CAN sniffer and custom traffic generator.
    """
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("🔧 God Mode - CAN Monitor & Injector")
        self.setGeometry(100, 100, 1200, 850)
        
        self.message_history = []
        self.max_history = 1000
        self.paused = False
        self.filter_enabled = False
        self.filter_ids = set()
        self.message_counter = 0
        self.auto_scroll_enabled = True
        
        self.continuous_sending = False
        self.continuous_timer = None
        
        self.random_active = False
        self.random_timer = None
        self.random_states = {}
        
        self.station_last_data = {}
        for station in range(STATION_COUNT):
            self.station_last_data[station] = {
                'R': {'value': None, 'time': None},
                'C': {'value': None, 'time': None},
                'O': {'value': None, 'time': None}
            }
        
        self.setup_ui()
        
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_station_times)
        self.update_timer.start(1000)
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        top_controls_layout = QHBoxLayout()
        
        can_mode_group = QGroupBox("🔌 CAN Controller Mode")
        can_mode_layout = QHBoxLayout()
        
        self.normal_mode_btn = QPushButton("🟢 Normal Mode")
        self.normal_mode_btn.clicked.connect(lambda: self.set_can_mode("NORMAL"))
        can_mode_layout.addWidget(self.normal_mode_btn)
        
        self.loopback_mode_btn = QPushButton("🔄 Loopback Mode")
        self.loopback_mode_btn.clicked.connect(lambda: self.set_can_mode("LOOPBACK"))
        can_mode_layout.addWidget(self.loopback_mode_btn)
        
        can_mode_group.setLayout(can_mode_layout)
        top_controls_layout.addWidget(can_mode_group)
        
        control_group = QGroupBox("⚙️ Control & Filters")
        control_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.toggled.connect(self.toggle_autoscroll)
        control_layout.addWidget(self.autoscroll_check)
        
        clear_btn = QPushButton("🗑 Clear")
        clear_btn.clicked.connect(self.clear_messages)
        control_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self.export_log)
        control_layout.addWidget(export_btn)
        
        control_layout.addWidget(QLabel("│"))
        
        self.filter_check = QCheckBox("Filter IDs:")
        self.filter_check.toggled.connect(self.toggle_filter)
        control_layout.addWidget(self.filter_check)
        
        self.filter_line = QLineEdit()
        self.filter_line.setPlaceholderText("0x100,0x101,0x102...")
        self.filter_line.setMaximumWidth(200)
        self.filter_line.textChanged.connect(self.update_filter_ids)
        self.filter_line.setEnabled(False)
        control_layout.addWidget(self.filter_line)
        
        control_layout.addWidget(QLabel("│"))
        
        self.msg_counter_label = QLabel("📊 Messages: 0 RX / 0 TX")
        control_layout.addWidget(self.msg_counter_label)
        self.rx_count = 0
        self.tx_count = 0
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        top_controls_layout.addWidget(control_group, stretch=1)
        
        main_layout.addLayout(top_controls_layout)
        
        main_content_layout = QHBoxLayout()
        
        left_column = QVBoxLayout()
        
        station_group = QGroupBox("📡 Station Status (Last Received)")
        station_layout = QVBoxLayout()
        
        self.station_table = QTableWidget()
        self.station_table.setColumnCount(7)
        self.station_table.setHorizontalHeaderLabels(["Station", "Roll", "Roll Δt", "Pitch", "Pitch Δt", "Yaw", "Yaw Δt"])
        self.station_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.station_table.setAlternatingRowColors(True)
        self.station_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        
        for i in range(STATION_COUNT):
            row = self.station_table.rowCount()
            self.station_table.insertRow(row)
            self.station_table.setItem(row, 0, QTableWidgetItem(f"0x10{i}"))
            for col in range(1, 7):
                self.station_table.setItem(row, col, QTableWidgetItem("--"))
        
        station_layout.addWidget(self.station_table)
        station_group.setLayout(station_layout)
        left_column.addWidget(station_group, stretch=1)
        
        tx_group = QGroupBox("📤 Send CAN Message")
        tx_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Manual Entry", "Angle Message", "LED Command", "Random Traffic"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        tx_layout.addLayout(mode_layout)
        
        self.tx_stack = QtWidgets.QStackedWidget()
        
        manual_widget = QWidget()
        manual_layout = QVBoxLayout()
        
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("CAN ID:"))
        self.manual_id_line = QLineEdit("0x100")
        self.manual_id_line.setMaximumWidth(100)
        id_layout.addWidget(self.manual_id_line)
        id_layout.addStretch()
        manual_layout.addLayout(id_layout)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Input format:"))
        self.manual_format_hex = QRadioButton("Hex")
        self.manual_format_ascii = QRadioButton("ASCII")
        self.manual_format_hex.setChecked(True)
        self.manual_format_hex.toggled.connect(self.on_manual_format_changed)
        format_layout.addWidget(self.manual_format_hex)
        format_layout.addWidget(self.manual_format_ascii)
        format_layout.addStretch()
        manual_layout.addLayout(format_layout)
        
        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("Data:"))
        self.manual_data_line = QLineEdit()
        self.manual_data_line.setPlaceholderText("e.g., 52 2D 33 34")
        data_layout.addWidget(self.manual_data_line)
        manual_layout.addLayout(data_layout)
        
        manual_send_btn = QPushButton("📨 Send Single Message")
        manual_send_btn.clicked.connect(self.send_manual_message)
        manual_layout.addWidget(manual_send_btn)
        
        manual_widget.setLayout(manual_layout)
        self.tx_stack.addWidget(manual_widget)
        
        angle_widget = QWidget()
        angle_layout = QVBoxLayout()
        
        angle_form = QHBoxLayout()
        angle_form.addWidget(QLabel("Group:"))
        self.angle_group_spin = QSpinBox()
        self.angle_group_spin.setRange(0, STATION_COUNT - 1)
        angle_form.addWidget(self.angle_group_spin)
        
        angle_form.addWidget(QLabel("Type:"))
        self.angle_type_combo = QComboBox()
        self.angle_type_combo.addItems(["R (Roll)", "C (Pitch)", "O (Yaw)"])
        angle_form.addWidget(self.angle_type_combo)
        
        angle_form.addWidget(QLabel("Value:"))
        self.angle_value_spin = QSpinBox()
        self.angle_value_spin.setRange(-179, 180)
        self.angle_value_spin.setValue(0)
        angle_form.addWidget(self.angle_value_spin)
        
        angle_form.addStretch()
        angle_layout.addLayout(angle_form)
        
        continuous_layout = QHBoxLayout()
        self.continuous_check = QCheckBox("Continuous send")
        continuous_layout.addWidget(self.continuous_check)
        continuous_layout.addWidget(QLabel("Period (ms):"))
        self.continuous_period_spin = QSpinBox()
        self.continuous_period_spin.setRange(50, 5000)
        self.continuous_period_spin.setValue(200)
        self.continuous_period_spin.setSingleStep(50)
        continuous_layout.addWidget(self.continuous_period_spin)
        continuous_layout.addStretch()
        angle_layout.addLayout(continuous_layout)
        
        angle_send_btn = QPushButton("📨 Send / Toggle Continuous")
        angle_send_btn.clicked.connect(self.send_angle_message)
        angle_layout.addWidget(angle_send_btn)
        
        angle_widget.setLayout(angle_layout)
        self.tx_stack.addWidget(angle_widget)
        
        led_widget = QWidget()
        led_layout = QVBoxLayout()
        
        led_form = QHBoxLayout()
        led_form.addWidget(QLabel("Target Group:"))
        self.led_group_spin = QSpinBox()
        self.led_group_spin.setRange(0, STATION_COUNT - 1)
        led_form.addWidget(self.led_group_spin)
        
        led_form.addWidget(QLabel("LEDs:"))
        self.led_r_check = QCheckBox("R")
        self.led_g_check = QCheckBox("G")
        self.led_b_check = QCheckBox("B")
        led_form.addWidget(self.led_r_check)
        led_form.addWidget(self.led_g_check)
        led_form.addWidget(self.led_b_check)
        
        led_form.addStretch()
        led_layout.addLayout(led_form)
        
        led_send_btn = QPushButton("📨 Send LED Command")
        led_send_btn.clicked.connect(self.send_led_command)
        led_layout.addWidget(led_send_btn)
        
        led_widget.setLayout(led_layout)
        self.tx_stack.addWidget(led_widget)
        
        random_widget = QWidget()
        random_layout = QVBoxLayout()
        
        random_form = QHBoxLayout()
        random_form.addWidget(QLabel("Groups:"))
        self.random_group_checks = []
        for i in range(STATION_COUNT):
            cb = QCheckBox(f"{i}")
            cb.setChecked(i == 0)
            self.random_group_checks.append(cb)
            random_form.addWidget(cb)
        
        select_all_btn = QPushButton("All")
        select_all_btn.setMaximumWidth(40)
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self.random_group_checks])
        random_form.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("None")
        select_none_btn.setMaximumWidth(40)
        select_none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self.random_group_checks])
        random_form.addWidget(select_none_btn)
        
        random_form.addStretch()
        random_layout.addLayout(random_form)
        
        mode_sel_frame = QGroupBox("Signal Mode per Group")
        mode_grid = QHBoxLayout()
        
        self.random_group_modes = []
        for i in range(STATION_COUNT):
            mode_combo = QComboBox()
            mode_combo.addItems(["Sine", "Const", "Noise"])
            mode_combo.setMaximumWidth(70)
            self.random_group_modes.append(mode_combo)
            
            mini_frame = QVBoxLayout()
            mini_frame.addWidget(QLabel(f"G{i}"))
            mini_frame.addWidget(mode_combo)
            mode_grid.addLayout(mini_frame)
        
        mode_sel_frame.setLayout(mode_grid)
        random_layout.addWidget(mode_sel_frame)
        
        random_control = QHBoxLayout()
        random_control.addWidget(QLabel("Period (ms):"))
        self.random_period_spin = QSpinBox()
        self.random_period_spin.setRange(50, 5000)
        self.random_period_spin.setValue(200)
        self.random_period_spin.setSingleStep(50)
        random_control.addWidget(self.random_period_spin)
        
        self.random_toggle_btn = QPushButton("▶ Start Random Traffic")
        self.random_toggle_btn.setCheckable(True)
        self.random_toggle_btn.toggled.connect(self.toggle_random_traffic)
        random_control.addWidget(self.random_toggle_btn)
        random_control.addStretch()
        random_layout.addLayout(random_control)
        
        random_widget.setLayout(random_layout)
        self.tx_stack.addWidget(random_widget)
        
        tx_layout.addWidget(self.tx_stack)
        tx_group.setLayout(tx_layout)
        left_column.addWidget(tx_group, stretch=1)
        
        main_content_layout.addLayout(left_column, stretch=2)
        
        right_column_paned = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        
        rx_group = QGroupBox("📥 Received CAN Messages")
        rx_layout = QVBoxLayout()
        
        self.rx_table = QTableWidget()
        self.rx_table.setColumnCount(6)
        self.rx_table.setHorizontalHeaderLabels(["Timestamp", "CAN ID", "DLC", "Type", "Data (Hex)", "Data (ASCII)"])
        self.rx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.rx_table.horizontalHeader().setStretchLastSection(True)
        self.rx_table.setAlternatingRowColors(True)
        self.rx_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rx_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        
        rx_layout.addWidget(self.rx_table)
        rx_group.setLayout(rx_layout)
        right_column_paned.addWidget(rx_group)
        
        log_group = QGroupBox("📋 Detailed Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtGui.QFont("Courier New", 9))
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right_column_paned.addWidget(log_group)
        
        right_column_paned.setStretchFactor(0, 3) # RX table gets 3/5 of space
        right_column_paned.setStretchFactor(1, 2) # Log gets 2/5 of space
        
        main_content_layout.addWidget(right_column_paned, stretch=3)
        
        main_layout.addLayout(main_content_layout)
    
    def set_can_mode(self, mode):
        if not self.main_window.serialConnected:
            self.log_text.append("❌ Not connected to serial port")
            return
        
        try:
            cmd = f"MODE_{mode}\n"
            self.main_window.serial.write(cmd.encode('utf-8'))
            self.log_text.append(f"✅ CAN mode set to: {mode}")
        except Exception as e:
            self.log_text.append(f"❌ Error setting CAN mode: {e}")
    
    def toggle_pause(self, checked):
        self.paused = checked
        self.pause_btn.setText("▶ Resume" if checked else "⏸ Pause")
    
    def toggle_autoscroll(self, checked):
        self.auto_scroll_enabled = checked
        
    def clear_messages(self):
        self.rx_table.setRowCount(0)
        self.message_history.clear()
        self.log_text.clear()
        self.message_counter = 0
        self.rx_count = 0
        self.tx_count = 0
        self.update_counter_label()
        
    def export_log(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Log", "can_log.txt", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    for msg in self.message_history:
                        f.write(f"{msg}\n")
                self.log_text.append(f"✅ Exported {len(self.message_history)} messages to {filename}")
            except Exception as e:
                self.log_text.append(f"❌ Export failed: {e}")
    
    def toggle_filter(self, checked):
        self.filter_enabled = checked
        self.filter_line.setEnabled(checked)
        
    def update_filter_ids(self, text):
        self.filter_ids.clear()
        for part in text.split(','):
            part = part.strip()
            if part:
                try:
                    can_id = int(part, 16) if part.startswith('0x') else int(part)
                    self.filter_ids.add(can_id)
                except ValueError:
                    pass
    
    def on_mode_changed(self, index):
        self.tx_stack.setCurrentIndex(index)
    
    def on_manual_format_changed(self):
        if self.manual_format_hex.isChecked():
            self.manual_data_line.setPlaceholderText("e.g., 52 2D 33 34")
        else:
            self.manual_data_line.setPlaceholderText("e.g., R-34")
    
    def update_counter_label(self):
        self.msg_counter_label.setText(f"📊 Messages: {self.rx_count} RX / {self.tx_count} TX")
    
    def on_can_message_received(self, msg):
        can_id = msg['can_id']
        data = msg['data']
        type_str = {'angle': 'Angle', 'led': 'LED', 'unknown': 'Unknown'}.get(msg['type'], 'Unknown')
        
        if self.paused:
            return
            
        if self.filter_enabled and can_id not in self.filter_ids:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hex_data = ' '.join(f'{b:02X}' for b in data)
        ascii_data = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
        
        msg_entry = f"[{timestamp}] ID=0x{can_id:03X} DLC={len(data)} Type={type_str} Data=[{hex_data}] ASCII=[{ascii_data}]"
        self.message_history.append(msg_entry)
        
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
            if self.rx_table.rowCount() > 0:
                self.rx_table.removeRow(0)
        
        self.rx_count += 1
        self.update_counter_label()
        
        row = self.rx_table.rowCount()
        self.rx_table.insertRow(row)
        
        self.message_counter += 1
        self.rx_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.rx_table.setItem(row, 1, QTableWidgetItem(f"0x{can_id:03X}"))
        self.rx_table.setItem(row, 2, QTableWidgetItem(str(len(data))))
        self.rx_table.setItem(row, 3, QTableWidgetItem(type_str))
        self.rx_table.setItem(row, 4, QTableWidgetItem(hex_data))
        self.rx_table.setItem(row, 5, QTableWidgetItem(ascii_data))
        
        if self.auto_scroll_enabled:
            self.rx_table.scrollToBottom()
        
        self.update_station_data(can_id, data, ascii_data)
    
    def update_station_data(self, can_id, data, ascii_data):
        if 0x100 <= can_id <= 0x100 + STATION_COUNT - 1:
            station = can_id - 0x100
            
            if len(data) >= 2 and ascii_data[0] in ['R', 'C', 'O']:
                angle_type = ascii_data[0]
                try:
                    angle_value = int(ascii_data[1:])
                    
                    self.station_last_data[station][angle_type] = {
                        'value': angle_value,
                        'time': time.time()
                    }
                    
                    self.refresh_station_table()
                    
                except ValueError:
                    pass
    
    def refresh_station_table(self):
        for station in range(STATION_COUNT):
            data = self.station_last_data[station]
            
            for idx, angle in enumerate(['R', 'C', 'O']):
                value_col = 1 + idx * 2
                time_col = 2 + idx * 2
                
                if data[angle]['value'] is not None:
                    self.station_table.setItem(station, value_col, 
                                              QTableWidgetItem(f"{data[angle]['value']}°"))
                    
                    elapsed = time.time() - data[angle]['time']
                    time_str = self.format_elapsed_time(elapsed)
                    self.station_table.setItem(station, time_col, 
                                              QTableWidgetItem(time_str))
                else:
                    self.station_table.setItem(station, value_col, QTableWidgetItem("--"))
                    self.station_table.setItem(station, time_col, QTableWidgetItem("--"))
    
    def update_station_times(self):
        self.refresh_station_table()
    
    def format_elapsed_time(self, seconds):
        if seconds < 1:
            return "now"
        elif seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds/3600)}h"
    
    def send_manual_message(self):
        try:
            can_id_text = self.manual_id_line.text().strip()
            can_id = int(can_id_text, 16) if can_id_text.startswith('0x') else int(can_id_text)
            
            data_text = self.manual_data_line.text().strip()
            
            if self.manual_format_hex.isChecked():
                data = bytes.fromhex(data_text.replace(' ', ''))
            else:
                data = data_text.encode('ascii')
            
            self._send_can_message(can_id, data)
            self.log_text.append(f"✅ Manual: ID=0x{can_id:03X}, Data={data.hex()} ({len(data)} bytes)")
        except Exception as e:
            self.log_text.append(f"❌ Manual send error: {e}")
    
    def send_angle_message(self):
        if self.continuous_check.isChecked():
            if self.continuous_sending:
                self.stop_continuous_sending()
            else:
                self.start_continuous_sending()
        else:
            self._send_single_angle()
    
    def _send_single_angle(self):
        try:
            group = self.angle_group_spin.value()
            angle_type = self.angle_type_combo.currentText()[0]
            value = self.angle_value_spin.value()
            
            can_id = 0x100 + group
            data = f"{angle_type}{value:+d}".encode('ascii')
            
            self._send_can_message(can_id, data)
            self.log_text.append(f"✅ Angle: G{group} {angle_type}={value}°")
        except Exception as e:
            self.log_text.append(f"❌ Angle send error: {e}")
    
    def start_continuous_sending(self):
        self.continuous_sending = True
        period = self.continuous_period_spin.value()
        
        self.continuous_timer = QtCore.QTimer()
        self.continuous_timer.timeout.connect(self._send_single_angle)
        self.continuous_timer.start(period)
        
        self.log_text.append(f"▶ Started continuous angle sending (period={period}ms)")
    
    def stop_continuous_sending(self):
        self.continuous_sending = False
        if self.continuous_timer:
            self.continuous_timer.stop()
            self.continuous_timer = None
        
        self.log_text.append("⏹ Stopped continuous angle sending")
    
    def send_led_command(self):
        try:
            group = self.led_group_spin.value()
            r = int(self.led_r_check.isChecked())
            g = int(self.led_g_check.isChecked())
            b = int(self.led_b_check.isChecked())
            
            try:
                message = self.main_window.protocol.build_led_command(group, r, g, b)
                self.main_window.serial.write(message)
                self.tx_count += 1
                self.update_counter_label()
                self.log_text.append(f"✅ LED: G{group} R={r} G={g} B={b}")
            except NotImplementedError:
                self.log_text.append("❌ LED command not implemented in protocol")
            
        except Exception as e:
            self.log_text.append(f"❌ LED send error: {e}")
    
    def toggle_random_traffic(self, checked):
        if checked:
            self.start_random_traffic()
        else:
            self.stop_random_traffic()
    
    def start_random_traffic(self):
        self.random_active = True
        period = self.random_period_spin.value()
        
        for i, cb in enumerate(self.random_group_checks):
            if cb.isChecked():
                mode = self.random_group_modes[i].currentText()
                self.random_states[i] = {
                    'mode': mode,
                    'start_time': time.time(),
                    'last_values': {'R': 0, 'C': 0, 'O': 0},
                    'const_value': random.randint(-90, 90),
                    'sine_params': {
                        'R': {'amp': random.randint(50, 120), 'period': random.uniform(5, 15), 
                              'phase': random.uniform(0, 2*math.pi), 'offset': random.randint(-50, 50)},
                        'C': {'amp': random.randint(50, 120), 'period': random.uniform(5, 15),
                              'phase': random.uniform(0, 2*math.pi), 'offset': random.randint(-50, 50)},
                        'O': {'amp': random.randint(50, 120), 'period': random.uniform(5, 15),
                              'phase': random.uniform(0, 2*math.pi), 'offset': random.randint(-50, 50)}
                    }
                }
        
        self.random_timer = QtCore.QTimer()
        self.random_timer.timeout.connect(self.send_random_traffic)
        self.random_timer.start(period)
        
        self.random_toggle_btn.setText("⏹ Stop Random Traffic")
        self.log_text.append(f"▶ Started random traffic (period={period}ms)")
    
    def stop_random_traffic(self):
        self.random_active = False
        if self.random_timer:
            self.random_timer.stop()
            self.random_timer = None
        
        self.random_states.clear()
        self.random_toggle_btn.setText("▶ Start Random Traffic")
        self.log_text.append("⏹ Stopped random traffic")
    
    def send_random_traffic(self):
        angle_types = ['R', 'C', 'O']
        
        for group_id, state in self.random_states.items():
            angle_type = random.choice(angle_types)
            mode = state['mode']
            
            if mode == "Sine":
                elapsed = time.time() - state['start_time']
                params = state['sine_params'][angle_type]
                value = params['amp'] * math.sin(2 * math.pi * elapsed / params['period'] + params['phase'])
                value = int(value + params['offset'] + random.uniform(-2, 2))
            elif mode == "Const":
                value = state['const_value']
            else:
                value = random.randint(-179, 180)
            
            value = max(-179, min(180, value))
            
            can_id = 0x100 + group_id
            data = f"{angle_type}{value:+d}".encode('ascii')
            
            try:
                self._send_can_message(can_id, data)
                self.log_text.append(f"🎲 Random: G{group_id} {angle_type}={value:+d}° [{mode}]")
            except Exception as e:
                logging.warning(f"Random traffic error: {e}")
                self.log_text.append(f"❌ Random error G{group_id}: {e}")
    
    def _send_can_message(self, can_id, data):
        if not self.main_window.serialConnected:
            raise Exception("Not connected to serial port")
        
        cmd = f"SEND_{can_id:x}"
        for byte in data:
            cmd += f"_{byte:02x}"
        cmd += "\n"
        
        self.main_window.serial.write(cmd.encode('utf-8'))
        self.tx_count += 1
        self.update_counter_label()
        
        logging.debug(f"[GodMode] Sent: {cmd.strip()}")
        
    def closeEvent(self, event):
        # Send reset command to firmware: NORMAL mode
        if self.main_window.serialConnected and self.main_window.serial.is_open:
            try:
                self.main_window.serial.write(b"MODE_NORMAL\n")
                self.main_window.serial.write(b"M1\n")
                logging.info("[GodMode] Sent reset command to firmware: NORMAL mode")
            except Exception as e:
                logging.warning(f"[GodMode] Failed to send reset commands on close: {e}")
        
        # Stop timers and accept the event
        self.stop_continuous_sending()
        self.stop_random_traffic()
        self.update_timer.stop()
        event.accept()