import sys
import time
import re
import html
import wmi
import pythoncom  

from device_registry import (
    get_vendor_name,
    is_trusted_device,
    get_trusted_name,
)

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QGraphicsDropShadowEffect,
    QSystemTrayIcon,
    QStyle,
)


class USBMonitor(QThread):
    device_event = pyqtSignal(str, dict)
    monitor_status = pyqtSignal(str, str)

    def __init__(self, poll_interval_ms=1000):
        super().__init__()
        self.poll_interval_ms = max(500, int(poll_interval_ms))

    def stop(self):
        self.requestInterruption()

    def get_usb_devices(self, wmi_conn):
        devices = {}

        wql = (
            "SELECT Name, Description, Manufacturer, PNPClass, PNPDeviceID "
            "FROM Win32_PnPEntity "
            "WHERE PNPDeviceID LIKE 'USB%' OR PNPDeviceID LIKE 'HID%'"
        )

        for device in wmi_conn.query(wql):
            try:
                pnp_id = str(device.PNPDeviceID or "").strip()
                name = str(device.Name or "Unknown USB Device").strip()
                description = str(device.Description or "No description available").strip()
                manufacturer = str(device.Manufacturer or "Unknown manufacturer").strip()
                device_class = str(device.PNPClass or "Unknown class").strip()

                searchable = f"{pnp_id} {name} {description} {manufacturer} {device_class}".upper()

                if not self.is_relevant_usb_device(searchable):
                    continue

                clean_name = self.clean_device_name(name)
                vid, pid = self.extract_vid_pid(pnp_id)
                routing_path = self.extract_routing(pnp_id)

                vendor_name = get_vendor_name(vid)
                trusted = is_trusted_device(vid, pid)
                trusted_name = get_trusted_name(vid, pid)

                resolved_manufacturer = manufacturer
                if vendor_name not in ["Unknown Vendor", "Unrecognized Vendor"]:
                    resolved_manufacturer = vendor_name

                fingerprint = self.create_fingerprint(pnp_id, vid, pid, clean_name)

                device_type, capabilities, anomaly_detected = self.analyze_hardware_profile(
                    clean_name,
                    description,
                    resolved_manufacturer,
                    device_class,
                )

                devices[fingerprint] = {
                    "id": pnp_id,
                    "fingerprint": fingerprint,
                    "name": trusted_name if trusted_name else clean_name,
                    "raw_name": name,
                    "description": description,
                    "manufacturer": resolved_manufacturer,
                    "class": device_class,
                    "type": device_type,
                    "capabilities": capabilities,
                    "anomaly": anomaly_detected,
                    "routing": routing_path,
                    "vid": vid,
                    "pid": pid,
                    "trusted": trusted,
                }

            except Exception:
                continue

        return devices

    def is_relevant_usb_device(self, text):
        keywords = [
            "USB",
            "HID",
            "KEYBOARD",
            "MOUSE",
            "STORAGE",
            "FLASH",
            "COMPOSITE",
            "INPUT",
        ]
        return any(keyword in text for keyword in keywords)

    def clean_device_name(self, name):
        if not name:
            return "Unknown USB Device"

        cleaned = name.strip()
        replacements = {
            "HID Keyboard Device": "Keyboard Input Node",
            "HID-compliant mouse": "Mouse Position Node",
            "USB Input Device": "USB Input Hub",
            "USB Composite Device": "Composite Interface Node",
            "USB Mass Storage Device": "Mass Storage Controller",
        }
        return replacements.get(cleaned, cleaned)

    def extract_vid_pid(self, pnp_id):
        vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", pnp_id or "")
        pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", pnp_id or "")

        vid = vid_match.group(1).upper() if vid_match else "Unknown"
        pid = pid_match.group(1).upper() if pid_match else "Unknown"

        return vid, pid

    def extract_routing(self, pnp_id):
        if not pnp_id:
            return "Direct Hub Route"

        parts = pnp_id.split("\\")
        return parts[-1] if len(parts) > 1 else "Direct Hub Route"

    def create_fingerprint(self, pnp_id, vid, pid, name):
        if pnp_id:
            return pnp_id.upper().strip()

        if vid != "Unknown" and pid != "Unknown":
            return f"{vid}:{pid}:{name.lower().strip()}"

        return name.lower().strip() or "unknown-device"

    def analyze_hardware_profile(self, name, description, manufacturer, device_class):
        text = f"{name} {description} {manufacturer}".lower()
        normalized_class = str(device_class or "").lower()

        capabilities = []
        anomaly_detected = False

        is_keyboard = "keyboard" in text or normalized_class == "keyboard"
        is_mouse = "mouse" in text or normalized_class == "mouse"
        is_storage = (
            any(k in text for k in ["mass storage", "storage", "disk", "flash"])
            or normalized_class in ["diskdrive", "volume"]
        )
        is_composite = "composite" in text
        is_hid = "hid" in text or normalized_class in ["hidclass", "hid"]
        is_camera = "camera" in text or "webcam" in text
        is_audio = any(k in text for k in ["audio", "headset", "microphone"])
        is_bluetooth = "bluetooth" in text

        known_input_vendor = any(
            vendor in text
            for vendor in [
                "mosart",
                "primax",
                "logitech",
                "microsoft",
                "razer",
                "lite-on",
                "dell",
                "hp",
                "lenovo",
            ]
        )

        if is_keyboard and known_input_vendor and is_hid:
            device_type = "HID Receiver / Input Device"
            capabilities.append("HID input receiver")
            capabilities.append("Pointer or keyboard-compatible interface")

        elif is_keyboard:
            device_type = "Keyboard Input Node"
            capabilities.append("Keyboard input interface")

        elif is_mouse:
            device_type = "Mouse Position Node"
            capabilities.append("Cursor Control")

        elif is_storage:
            device_type = "Mass Storage Controller"
            capabilities.append("File Pipeline Execution")

        elif is_composite:
            device_type = "Composite Interface Node"
            capabilities.append("Multi-Channel Tunneling")

        elif is_hid:
            device_type = "HID Interface Node"
            capabilities.append("Raw HID Input Channel")

        elif is_camera:
            device_type = "Camera Interface Node"
            capabilities.append("Video Capture Interface")

        elif is_audio:
            device_type = "Audio Interface Node"
            capabilities.append("Audio Input/Output Interface")

        elif is_bluetooth:
            device_type = "Bluetooth Adapter Node"
            capabilities.append("Wireless Device Bridge")

        else:
            device_type = "USB Peripheral"
            capabilities.append("Standard Peripheral I/O")

        if (
            "keyboard" in text
            and not known_input_vendor
            and normalized_class not in ["keyboard", "hidclass", "hid"]
            and not is_composite
        ):
            anomaly_detected = True
            capabilities.append("Class Mismatch Signature")

        return device_type, capabilities, anomaly_detected

    def pick_best_device(self, device_list):
        if not device_list:
            return None

        anomalous_devices = [device for device in device_list if device.get("anomaly")]
        if anomalous_devices:
            return anomalous_devices[0]

        priority = [
            "Keyboard Input Node",
            "Mass Storage Controller",
            "Composite Interface Node",
            "HID Receiver / Input Device",
            "HID Interface Node",
            "Mouse Position Node",
            "Camera Interface Node",
            "Audio Interface Node",
            "Bluetooth Adapter Node",
            "USB Peripheral",
        ]

        for device_type in priority:
            for device in device_list:
                if device.get("type") == device_type:
                    return device

        return device_list[0]

    def run(self):
        com_initialized = False
        last_error_log = 0

        try:
            pythoncom.CoInitialize()
            com_initialized = True

            wmi_conn = wmi.WMI()
            previous_devices = self.get_usb_devices(wmi_conn)

            self.monitor_status.emit(
                "READY",
                f"Baseline scan completed. {len(previous_devices)} USB interface(s) currently visible.",
            )

            while not self.isInterruptionRequested():
                self.msleep(self.poll_interval_ms)

                if self.isInterruptionRequested():
                    break

                try:
                    current_devices = self.get_usb_devices(wmi_conn)
                except Exception as error:
                    now = time.time()
                    if now - last_error_log > 5:
                        self.monitor_status.emit("ERROR", f"WMI scan failed: {error}")
                        last_error_log = now
                    continue

                previous_ids = set(previous_devices.keys())
                current_ids = set(current_devices.keys())

                new_ids = current_ids - previous_ids
                removed_ids = previous_ids - current_ids

                if new_ids:
                    new_devices = [current_devices[device_id] for device_id in new_ids]
                    best_device = self.pick_best_device(new_devices)
                    if best_device:
                        self.device_event.emit("connected", best_device)

                if removed_ids:
                    removed_devices = [previous_devices[device_id] for device_id in removed_ids]
                    best_device = self.pick_best_device(removed_devices)
                    if best_device:
                        self.device_event.emit("removed", best_device)

                previous_devices = current_devices

        except Exception as error:
            self.monitor_status.emit("ERROR", f"USB monitor failed to start: {error}")

        finally:
            if com_initialized:
                pythoncom.CoUninitialize()


class PortSentinel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PortSentinel v2.7")
        self.setGeometry(150, 100, 1250, 780)

        self.total_events = 0
        self.connected_count = 0
        self.removed_count = 0
        self.session_history = set()
        self.last_event = {"type": None, "fingerprint": None, "time": 0}

        self.setStyleSheet("""
            QWidget {
                background-color: #0E1012; 
                color: #D1D5DB;
                font-family: 'Outfit', 'Century Gothic', 'Avenir', 'Trebuchet MS', sans-serif;
                font-size: 15px; 
            }
            
            QFrame#sidebar {
                background-color: #14171C;
                border-right: 1px solid #1D212A;
            }
            
            QLabel#logoTitle {
                font-family: 'Space Grotesk', 'Outfit', 'Century Gothic', sans-serif;
                font-size: 28px; 
                font-weight: 800;
                color: #F77F6E; 
                letter-spacing: 0.5px;
            }
            
            QLabel#logoSub {
                font-size: 13px;
                color: #526075;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 600;
            }

            QLabel#engineBadge {
                background-color: #0F1216;
                border: 1px solid #334155;
                color: #F8FAFC;
                border-radius: 8px; 
                font-weight: 700;
                font-size: 13px;
                padding: 16px;
            }

            QFrame#metricBox {
                background-color: #171A21;
                border: 1px solid #262B36;
                border-radius: 12px;
            }
            QLabel#numDisplay {
                font-size: 38px; 
                font-weight: 500; 
                color: #F1F5F9;
            }
            QLabel#textLabel {
                font-size: 12px;
                font-weight: 500; 
                color: #8B9BB4;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }

            QTextEdit#telemetryConsole {
                background-color: #08090C;
                border: 1px solid #1D212A;
                border-radius: 14px;
                padding: 22px;
                color: #E2E8F0; 
                font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
                font-size: 15px; 
                line-height: 1.6;
            }

            QPushButton#actionBtn {
                background-color: #191D24;
                color: #F1F5F9;
                border: 1px solid #2A313D;
                padding: 14px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                letter-spacing: 0.5px;
            }
            QPushButton#actionBtn:hover {
                background-color: #F77F6E;
                border-color: #F77F6E;
                color: #FFFFFF;
            }
            QPushButton#actionBtn:pressed {
                background-color: #DD6B5B;
            }
            
            QScrollBar:vertical {
                width: 7px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #222832;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #F77F6E;
            }
        """)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 28, 24, 28)
        sidebar_layout.setSpacing(24)

        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(4)
        self.logo = QLabel("PortSentinel")
        self.logo.setObjectName("logoTitle")
        self.sub_logo = QLabel("Intelligent I/O Analytics")
        self.sub_logo.setObjectName("logoSub")
        brand_layout.addWidget(self.logo)
        brand_layout.addWidget(self.sub_logo)
        sidebar_layout.addLayout(brand_layout)

        self.engine_badge = QLabel("LIVE THREAT ENGINE\n🟢 Operational / Scanning")
        self.engine_badge.setObjectName("engineBadge")
        self.engine_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.engine_badge)

        counters_title = QLabel("Activity Indicators")
        counters_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #4B5563; text-transform: uppercase; letter-spacing: 1px;")
        sidebar_layout.addWidget(counters_title)

        self.card_total, self.lbl_total = self.create_sidebar_counter("0", "Evaluations Run")
        self.card_conn, self.lbl_conn = self.create_sidebar_counter("0", "Active Node Mounts")
        self.card_rem, self.lbl_rem = self.create_sidebar_counter("0", "Dropped Connections")

        sidebar_layout.addWidget(self.card_total)
        sidebar_layout.addWidget(self.card_conn)
        sidebar_layout.addWidget(self.card_rem)
        sidebar_layout.addStretch()

        self.clear_btn = QPushButton("Clear Activity Log")
        self.clear_btn.setObjectName("actionBtn")
        self.clear_btn.clicked.connect(self.clear_logs)
        sidebar_layout.addWidget(self.clear_btn)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(28, 28, 28, 28)
        workspace_layout.setSpacing(18)

        workspace_header = QHBoxLayout()
        ws_title_block = QVBoxLayout()
        ws_title = QLabel("Hardware Telemetry Stream")
        ws_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #F8FAFC;")
        ws_desc = QLabel("Asynchronous core bus tracking analyzing physical device class footprints and spoof layers.")
        ws_desc.setStyleSheet("font-size: 14px; color: #64748B;")
        ws_title_block.addWidget(ws_title)
        ws_title_block.addWidget(ws_desc)
        workspace_header.addLayout(ws_title_block)
        workspace_layout.addLayout(workspace_header)

        self.log_box = QTextEdit()
        self.log_box.setObjectName("telemetryConsole")
        self.log_box.setReadOnly(True)
        self.log_box.document().setMaximumBlockCount(1500)

        self.setup_notifications()

        self.append_system_message("SYSTEM", "Interface monitoring architecture initialized cleanly.")
        self.append_system_message("SYSTEM", "High-speed WQL polling active.")
        self.append_system_message("SYSTEM", "Desktop notifications enabled.")
        self.append_system_message("READY", "Awaiting physical device mount activity...")

        workspace_layout.addWidget(self.log_box)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(workspace)

        self.monitor = USBMonitor()
        self.monitor.device_event.connect(self.handle_usb_event)
        self.monitor.monitor_status.connect(self.append_system_message)
        self.monitor.start()

    def create_sidebar_counter(self, number, title_text):
        frame = QFrame()
        frame.setObjectName("metricBox")

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setXOffset(0)
        glow.setYOffset(0)
        glow.setColor(QColor(140, 190, 255, 45))
        frame.setGraphicsEffect(glow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)
        num_label = QLabel(number)
        num_label.setObjectName("numDisplay")
        text_label = QLabel(title_text)
        text_label.setObjectName("textLabel")
        layout.addWidget(num_label)
        layout.addWidget(text_label)
        return frame, num_label

    def setup_notifications(self):
        self.tray_icon = None
        self.notifications_enabled = QSystemTrayIcon.isSystemTrayAvailable()

        if not self.notifications_enabled:
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.tray_icon.setToolTip("PortSentinel USB Threat Monitor")
        self.tray_icon.show()

    def send_usb_notification(self, event_type, device, risk=None):
        if not getattr(self, "notifications_enabled", False):
            return

        if self.tray_icon is None:
            return

        try:
            device_name = str(device.get("name", "Unknown USB Device"))
            vid = str(device.get("vid", "Unknown"))
            pid = str(device.get("pid", "Unknown"))

            icon = QSystemTrayIcon.MessageIcon.Information
            duration = 4500

            if event_type == "connected":
                risk = risk or {"score": 0, "level": "LOW"}
                level = str(risk.get("level", "LOW"))
                score = risk.get("score", 0)

                if device.get("trusted"):
                    title = "PortSentinel: Trusted USB Connected"
                    message = f"{device_name}\nRisk Score: {score}/100\nVID/PID: {vid} / {pid}"

                elif level == "HIGH":
                    title = "PortSentinel: High-Risk USB Detected"
                    message = f"{device_name}\nRisk Score: {score}/100\nDisconnect if you do not recognize this device."
                    icon = QSystemTrayIcon.MessageIcon.Critical
                    duration = 9000

                elif level == "MEDIUM":
                    title = "PortSentinel: Unverified USB Device"
                    message = f"{device_name}\nRisk Score: {score}/100\nReview this device before trusting it."
                    icon = QSystemTrayIcon.MessageIcon.Warning
                    duration = 7000

                else:
                    title = "PortSentinel: USB Device Connected"
                    message = f"{device_name}\nRisk Score: {score}/100\nVID/PID: {vid} / {pid}"

            elif event_type == "removed":
                title = "PortSentinel: USB Device Removed"
                message = f"{device_name}\nVID/PID: {vid} / {pid}"
                duration = 3500

            else:
                return

            self.tray_icon.showMessage(title, message, icon, duration)

        except Exception as error:
            self.append_system_message("NOTICE", f"Notification failed: {error}")

    def safe_html(self, value):
        return html.escape(str(value))

    def append_system_message(self, status, msg):
        timestamp = time.strftime("%H:%M:%S")
        safe_status = self.safe_html(status)
        safe_msg = self.safe_html(msg)

        self.log_box.append(
            f'<span style="color: #64748B;">[{timestamp}]</span> '
            f'<span style="color: #F77F6E; font-weight: 700;">[{safe_status}]</span> '
            f'<span style="color: #E2E8F0;">{safe_msg}</span>'
        )
        self.scroll_log_to_bottom()

    def handle_usb_event(self, event_type, device):
        current_time = time.time()
        fingerprint = device.get("fingerprint", device.get("name", "unknown"))

        if (self.last_event["type"] == event_type and
                self.last_event["fingerprint"] == fingerprint and
                current_time - self.last_event["time"] < 0.9):
            return

        self.last_event = {"type": event_type, "fingerprint": fingerprint, "time": current_time}
        self.total_events += 1

        if event_type == "connected":
            self.connected_count += 1
            risk = self.estimate_risk(device)
            self.update_engine_status(risk)
            self.send_usb_notification("connected", device, risk)

            is_new = fingerprint not in self.session_history
            self.session_history.add(fingerprint)
            session_tag = "<b style='color: #F77F6E;'>[FIRST-SEEN IN SESSION]</b>" if is_new else "<b style='color: #94A3B8;'>[RECOGNIZED INSTANCE]</b>"

            accent_color = "#F77F6E"
            if risk["level"] == "LOW":
                accent_color = "#94A3B8"
            elif risk["level"] == "MEDIUM":
                accent_color = "#E5A45B"
            elif risk["level"] == "HIGH":
                accent_color = "#E05A6B"

            caps = device.get("capabilities", ["Standard Base Interface"])
            caps_html = "".join(
                f"<span style='background-color: #1A1E26; color: #E2E8F0; padding: 4px 10px; border-radius: 6px; margin-right: 6px; font-size: 13px; font-weight: 600; font-family: sans-serif;'>{self.safe_html(c)}</span>"
                for c in caps
            )

            anomaly_banner = ""
            if device.get("anomaly"):
                anomaly_banner = "<tr style='color: #E05A6B;'><td><b>Alert Header:</b></td><td><b>🚨 CRITICAL CLASS MISMATCH (SPOOF VECTOR SUSPECTED)</b></td></tr>"

            safe_name = self.safe_html(device.get("name", "Unknown Device"))
            safe_manufacturer = self.safe_html(device.get("manufacturer", "Unknown manufacturer"))
            safe_routing = self.safe_html(device.get("routing", "Direct Route"))
            safe_vid = self.safe_html(device.get("vid", "Unknown"))
            safe_pid = self.safe_html(device.get("pid", "Unknown"))
            safe_reason = self.safe_html(risk.get("reason", "No reason supplied."))

            html_log = f"""
            <div style="margin-top: 14px; margin-bottom: 14px; border-left: 4px solid {accent_color}; padding-left: 16px; background-color: #12151B; padding-top: 16px; padding-bottom: 16px; border-radius: 0px 10px 10px 0px;">
                <b style="color: {accent_color}; font-size: 16px; font-family: 'Outfit', sans-serif;">📡 HARDWARE PORT INTERCONNECT ESTABLISHED</b> &nbsp; {session_tag}<br>
                <table cellspacing="8" cellpadding="0" style="color: #CBD5E1; font-size: 14px; margin-top: 12px; width: 100%;">
                    {anomaly_banner}
                    <tr><td width="200"><b>Device Identity:</b></td><td><span style="color: #FFFFFF; font-weight: 700; font-size: 15px;">{safe_name}</span></td></tr>
                    <tr><td><b>Manufacturer String:</b></td><td>{safe_manufacturer}</td></tr>
                    <tr><td><b>Bus Mapping Route:</b></td><td><code style="color: #94A3B8;">{safe_routing}</code></td></tr>
                    <tr><td><b>Hardware ID Keys:</b></td><td><code style="color: #E2E8F0;">VID_{safe_vid} / PID_{safe_pid}</code></td></tr>
                    <tr><td><b>Mapped Capabilities:</b></td><td>{caps_html}</td></tr>
                    <tr><td><b>Threat Score Assessment:</b></td><td><span style="color: {accent_color}; font-weight: 700;">{risk['score']}/100 ({risk['level']} RISK)</span></td></tr>
                    <tr><td><b>Forensic Logic:</b></td><td><i style="color: #94A3B8;">{safe_reason}</i></td></tr>
                </table>
            </div>
            """
            self.log_box.append(html_log)

        elif event_type == "removed":
            self.removed_count += 1
            self.send_usb_notification("removed", device)

            safe_name = self.safe_html(device.get("name", "Unknown Device"))
            safe_routing = self.safe_html(device.get("routing", "Direct Route"))

            html_log = f"""
            <div style="margin-top: 14px; margin-bottom: 14px; border-left: 4px solid #3A4454; padding-left: 16px; background-color: #12151B; padding-top: 14px; padding-bottom: 14px; border-radius: 0px 10px 10px 0px;">
                <b style="color: #94A3B8; font-size: 15px; font-family: 'Outfit', sans-serif;">🔌 PERIPHERAL RELEVANCE DISCONNECT</b><br>
                <span style="color: #CBD5E1; font-size: 14px; display: inline-block; margin-top: 8px;">
                    Node descriptor <b style="color: #FFFFFF;">{safe_name}</b> dropped routing path alignment from <code style="color: #94A3B8;">{safe_routing}</code>.
                </span>
            </div>
            """
            self.log_box.append(html_log)

        self.lbl_total.setText(str(self.total_events))
        self.lbl_conn.setText(str(self.connected_count))
        self.lbl_rem.setText(str(self.removed_count))
        self.scroll_log_to_bottom()

    def update_engine_status(self, risk):
        if risk["level"] == "HIGH":
            self.engine_badge.setText("LIVE THREAT ENGINE\n🔴 Critical Alert Detected")
            self.engine_badge.setStyleSheet("background-color: #261618; border: 1px solid #E05A6B; color: #E05A6B; font-weight: 700; padding: 14px; border-radius: 8px;")
        elif risk["level"] == "MEDIUM":
            self.engine_badge.setText("LIVE THREAT ENGINE\n🟠 Analyzing Unverified")
            self.engine_badge.setStyleSheet("background-color: #262116; border: 1px solid #E5A45B; color: #E5A45B; font-weight: 700; padding: 14px; border-radius: 8px;")
        else:
            self.engine_badge.setText("LIVE THREAT ENGINE\n🟢 Operational / Scanning")
            self.engine_badge.setStyleSheet("background-color: #0F1216; border: 1px solid #334155; color: #F8FAFC; font-weight: 700; padding: 14px; border-radius: 8px;")

    def estimate_risk(self, device):
        if device.get("trusted"):
            return {
                "score": 0,
                "level": "LOW",
                "reason": "Hardware matched inside environment whitelist registries.",
                "recommendation": "Pass-through authorized.",
            }

        score = 0
        reasons = []

        device_type = str(device.get("type", "USB Peripheral")).lower()
        device_class = str(device.get("class", "Unknown class")).lower()
        manufacturer = str(device.get("manufacturer", "Unknown manufacturer")).lower()
        name = str(device.get("name", "Unknown Device")).lower()

        known_input_vendor = any(
            vendor in manufacturer
            for vendor in [
                "mosart",
                "primax",
                "logitech",
                "microsoft",
                "razer",
                "lite-on",
                "dell",
                "hp",
                "lenovo",
            ]
        )

        if device.get("anomaly"):
            score += 45
            reasons.append("Structural anomalies detected.")

        if "keyboard" in device_type:
            if known_input_vendor:
                score += 10
                reasons.append("Keyboard-compatible HID interface exposed by a known input-device vendor.")
            else:
                score += 30
                reasons.append("Keyboard interface can process automated input.")

        if "hid" in device_type or "hid" in device_class:
            if known_input_vendor:
                score += 5
                reasons.append("Known HID input-device vendor detected.")
            else:
                score += 20
                reasons.append("Raw Human Interface Device channel exposed.")

        if "receiver" in device_type:
            score += 5
            reasons.append("USB input receiver detected.")

        if "composite" in device_type:
            score += 20
            reasons.append("Exposes multiple interface channels through a composite controller.")

        if "storage" in device_type:
            score += 15
            reasons.append("Exposes mountable active file allocation directory channels.")

        if any(v in manufacturer for v in ["unknown", "unrecognized", "pending", "unavailable"]):
            score += 15
            reasons.append("Lacks registered physical vendor verification keys.")

        suspicious_identity = f"{name} {manufacturer}"
        if any(s in suspicious_identity for s in ["ducky", "badusb", "teensy", "arduino", "whid"]):
            score += 55
            reasons.append("Signature explicitly matches high-priority attack injection kits.")

        score = min(score, 100)

        level = "LOW"
        if score >= 60:
            level = "HIGH"
        elif score >= 30:
            level = "MEDIUM"

        return {
            "score": score,
            "level": level,
            "reason": " • ".join(reasons) if reasons else "Generic baseline metrics footprint verified clean.",
        }

    def scroll_log_to_bottom(self):
        cursor = self.log_box.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_box.setTextCursor(cursor)
        self.log_box.ensureCursorVisible()

    def clear_logs(self):
        self.log_box.clear()
        self.append_system_message("PURGE", "Local live monitor terminal display buffer cleared down.")

    def closeEvent(self, event):
        if hasattr(self, "monitor") and self.monitor.isRunning():
            self.monitor.stop()
            self.monitor.wait(2500)

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PortSentinel()
    window.show()
    sys.exit(app.exec())
