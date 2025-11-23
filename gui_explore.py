"""
Exploration widget for the GUI.
"""
import logging
import yaml
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QTextEdit, QFileDialog, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from cli_explorer import TestbedCLIExplorer
from trie import CommandTrie


logger = logging.getLogger(__name__)


class ExplorationThread(QThread):
    """Thread for running CLI exploration."""

    progress = Signal(str)
    finished = Signal(CommandTrie, str)
    error = Signal(str)

    def __init__(self, testbed_file, device_name, output_file, max_depth, delay):
        super().__init__()
        self.testbed_file = testbed_file
        self.device_name = device_name
        self.output_file = output_file
        self.max_depth = max_depth
        self.delay = delay

    def run(self):
        """Run the exploration."""
        try:
            self.progress.emit("Starting exploration...")

            explorer = TestbedCLIExplorer(
                testbed_file=self.testbed_file,
                device_name=self.device_name,
                max_depth=self.max_depth,
                delay=self.delay
            )

            trie = explorer.explore(output_file=self.output_file)

            self.progress.emit("Exploration complete!")
            self.finished.emit(trie, self.output_file)

        except Exception as e:
            logger.error(f"Exploration failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ExploreWidget(QWidget):
    """Widget for device exploration configuration."""

    exploration_complete = Signal(CommandTrie, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.exploration_thread = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("<h2>Explore Cisco Device CLI</h2>")
        layout.addWidget(title)

        # Testbed configuration group
        testbed_group = QGroupBox("Testbed Configuration")
        testbed_layout = QFormLayout()

        self.testbed_file_edit = QLineEdit()
        testbed_browse_btn = QPushButton("Browse...")
        testbed_browse_btn.clicked.connect(self.browse_testbed_file)

        testbed_file_layout = QHBoxLayout()
        testbed_file_layout.addWidget(self.testbed_file_edit)
        testbed_file_layout.addWidget(testbed_browse_btn)

        testbed_layout.addRow("Testbed File:", testbed_file_layout)

        self.device_name_edit = QLineEdit()
        self.device_name_edit.setPlaceholderText("e.g., router1")
        testbed_layout.addRow("Device Name:", self.device_name_edit)

        testbed_group.setLayout(testbed_layout)
        layout.addWidget(testbed_group)

        # Quick testbed creator
        quick_testbed_btn = QPushButton("Create Quick Testbed...")
        quick_testbed_btn.clicked.connect(self.show_quick_testbed)
        layout.addWidget(quick_testbed_btn)

        # Exploration settings group
        settings_group = QGroupBox("Exploration Settings")
        settings_layout = QFormLayout()

        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(1, 50)
        self.max_depth_spin.setValue(10)
        settings_layout.addRow("Max Depth:", self.max_depth_spin)

        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 10.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.5)
        self.delay_spin.setSuffix(" seconds")
        settings_layout.addRow("Command Delay:", self.delay_spin)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()

        self.output_file_edit = QLineEdit()
        self.output_file_edit.setText("commands.json")
        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self.browse_output_file)

        output_file_layout = QHBoxLayout()
        output_file_layout.addWidget(self.output_file_edit)
        output_file_layout.addWidget(output_browse_btn)

        output_layout.addRow("Output File:", output_file_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Exploration")
        self.start_btn.clicked.connect(self.start_exploration)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_exploration)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)

        # Add stretch to push everything to the top
        layout.addStretch()

        self.setLayout(layout)

    def browse_testbed_file(self):
        """Browse for testbed file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Testbed File",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if file_path:
            self.testbed_file_edit.setText(file_path)

    def browse_output_file(self):
        """Browse for output file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "commands.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.output_file_edit.setText(file_path)

    def show_quick_testbed(self):
        """Show quick testbed creator dialog."""
        from gui_testbed import QuickTestbedDialog

        dialog = QuickTestbedDialog(self)
        if dialog.exec():
            testbed_file = dialog.get_testbed_file()
            if testbed_file:
                self.testbed_file_edit.setText(testbed_file)

    def start_exploration(self):
        """Start the CLI exploration."""
        # Validate inputs
        testbed_file = self.testbed_file_edit.text().strip()
        device_name = self.device_name_edit.text().strip()
        output_file = self.output_file_edit.text().strip()

        if not testbed_file:
            QMessageBox.warning(self, "Missing Input", "Please select a testbed file")
            return

        if not device_name:
            QMessageBox.warning(self, "Missing Input", "Please enter a device name")
            return

        if not output_file:
            QMessageBox.warning(self, "Missing Input", "Please enter an output file")
            return

        # Check if testbed file exists
        if not Path(testbed_file).exists():
            QMessageBox.warning(self, "File Not Found", f"Testbed file not found:\n{testbed_file}")
            return

        # Disable start button, enable stop button
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.show()
        self.status_label.setText("Exploring...")

        # Start exploration thread
        self.exploration_thread = ExplorationThread(
            testbed_file=testbed_file,
            device_name=device_name,
            output_file=output_file,
            max_depth=self.max_depth_spin.value(),
            delay=self.delay_spin.value()
        )

        self.exploration_thread.progress.connect(self.on_progress)
        self.exploration_thread.finished.connect(self.on_finished)
        self.exploration_thread.error.connect(self.on_error)

        self.exploration_thread.start()

    def stop_exploration(self):
        """Stop the exploration."""
        if self.exploration_thread and self.exploration_thread.isRunning():
            self.exploration_thread.terminate()
            self.exploration_thread.wait()
            self.on_stopped()

    def on_progress(self, message):
        """Handle progress update."""
        self.status_label.setText(message)

    def on_finished(self, trie, file_path):
        """Handle exploration completion."""
        self.progress_bar.hide()
        self.status_label.setText(f"Complete! Found {trie.total_commands} commands")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # Emit signal to main window
        self.exploration_complete.emit(trie, file_path)

    def on_error(self, error_msg):
        """Handle exploration error."""
        self.progress_bar.hide()
        self.status_label.setText("Error during exploration")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        QMessageBox.critical(self, "Exploration Error", f"Exploration failed:\n\n{error_msg}")

    def on_stopped(self):
        """Handle exploration stopped."""
        self.progress_bar.hide()
        self.status_label.setText("Exploration stopped by user")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
