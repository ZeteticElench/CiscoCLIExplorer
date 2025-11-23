"""
Quick testbed creator dialog for the GUI.
"""
import yaml
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGroupBox, QFormLayout, QComboBox, QSpinBox,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt


logger = logging.getLogger(__name__)


class QuickTestbedDialog(QDialog):
    """Dialog for quickly creating a testbed file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.testbed_file = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Quick Testbed Creator")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout()

        # Title
        title = QLabel("<h2>Create Quick Testbed</h2>")
        layout.addWidget(title)

        # Device settings group
        device_group = QGroupBox("Device Settings")
        device_layout = QFormLayout()

        self.device_name_edit = QLineEdit()
        self.device_name_edit.setText("router1")
        device_layout.addRow("Device Name:", self.device_name_edit)

        self.os_combo = QComboBox()
        self.os_combo.addItems(["iosxe", "ios", "iosxr", "nxos", "asa"])
        device_layout.addRow("Operating System:", self.os_combo)

        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems(["router", "switch", "firewall"])
        device_layout.addRow("Device Type:", self.device_type_combo)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # Connection settings group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["ssh", "telnet"])
        conn_layout.addRow("Protocol:", self.protocol_combo)

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("e.g., 192.168.1.1")
        conn_layout.addRow("IP Address:", self.ip_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        self.protocol_combo.currentTextChanged.connect(self.on_protocol_changed)
        conn_layout.addRow("Port:", self.port_spin)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Credentials group
        cred_group = QGroupBox("Credentials")
        cred_layout = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("e.g., admin")
        cred_layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter password...")
        cred_layout.addRow("Password:", self.password_edit)

        self.enable_password_edit = QLineEdit()
        self.enable_password_edit.setEchoMode(QLineEdit.Password)
        self.enable_password_edit.setPlaceholderText("Enter enable password (optional)...")
        cred_layout.addRow("Enable Password:", self.enable_password_edit)

        cred_group.setLayout(cred_layout)
        layout.addWidget(cred_group)

        # Save location
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("Save As:"))

        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText("testbed.yaml")
        save_layout.addWidget(self.save_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_save_location)
        save_layout.addWidget(browse_btn)

        layout.addLayout(save_layout)

        # Buttons
        button_layout = QHBoxLayout()

        create_btn = QPushButton("Create Testbed")
        create_btn.clicked.connect(self.create_testbed)
        create_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def on_protocol_changed(self, protocol):
        """Handle protocol change."""
        if protocol == "ssh":
            self.port_spin.setValue(22)
        elif protocol == "telnet":
            self.port_spin.setValue(23)

    def browse_save_location(self):
        """Browse for save location."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Testbed File",
            "testbed.yaml",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if file_path:
            self.save_path_edit.setText(file_path)

    def create_testbed(self):
        """Create the testbed file."""
        # Validate inputs
        device_name = self.device_name_edit.text().strip()
        ip_address = self.ip_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        save_path = self.save_path_edit.text().strip()

        if not device_name:
            QMessageBox.warning(self, "Missing Input", "Please enter a device name")
            return

        if not ip_address:
            QMessageBox.warning(self, "Missing Input", "Please enter an IP address")
            return

        if not username:
            QMessageBox.warning(self, "Missing Input", "Please enter a username")
            return

        if not password:
            QMessageBox.warning(self, "Missing Input", "Please enter a password")
            return

        if not save_path:
            QMessageBox.warning(self, "Missing Input", "Please enter a save path")
            return

        try:
            # Build testbed structure
            testbed = {
                'devices': {
                    device_name: {
                        'os': self.os_combo.currentText(),
                        'type': self.device_type_combo.currentText(),
                        'connections': {
                            'cli': {
                                'protocol': self.protocol_combo.currentText(),
                                'ip': ip_address,
                                'port': self.port_spin.value()
                            }
                        },
                        'credentials': {
                            'default': {
                                'username': username,
                                'password': password
                            }
                        }
                    }
                }
            }

            # Add enable password if provided
            enable_password = self.enable_password_edit.text()
            if enable_password:
                testbed['devices'][device_name]['credentials']['enable'] = {
                    'password': enable_password
                }

            # Save to file
            with open(save_path, 'w') as f:
                yaml.dump(testbed, f, default_flow_style=False)

            self.testbed_file = save_path

            QMessageBox.information(
                self,
                "Success",
                f"Testbed file created successfully:\n{save_path}"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create testbed file:\n{str(e)}"
            )
            logger.error(f"Failed to create testbed: {e}", exc_info=True)

    def get_testbed_file(self):
        """Get the created testbed file path."""
        return self.testbed_file
