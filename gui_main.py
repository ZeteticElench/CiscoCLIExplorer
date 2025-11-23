#!/usr/bin/env python3
"""
PySide6 GUI for Cisco CLI Explorer.
"""
import sys
import os
import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTabWidget,
    QTextEdit, QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar,
    QToolBar, QLineEdit, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QAction, QIcon, QFont
from trie import CommandTrie


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for the CLI Explorer GUI."""

    def __init__(self):
        super().__init__()
        self.current_trie = None
        self.current_file = None

        self.init_ui()
        self.setup_logging()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Cisco CLI Explorer - PyATS")
        self.setGeometry(100, 100, 1200, 800)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create tabs
        self.create_explore_tab()
        self.create_viewer_tab()
        self.create_neo4j_tab()
        self.create_logs_tab()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open JSON...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_json_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Save As...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_json_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        explore_action = QAction("&Explore Device...", self)
        explore_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        tools_menu.addAction(explore_action)

        neo4j_action = QAction("Export to &Neo4j...", self)
        neo4j_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        tools_menu.addAction(neo4j_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Create the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Open button
        open_btn = QAction("Open", self)
        open_btn.triggered.connect(self.open_json_file)
        toolbar.addAction(open_btn)

        # Save button
        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self.save_json_file)
        toolbar.addAction(save_btn)

        toolbar.addSeparator()

        # Refresh viewer button
        refresh_btn = QAction("Refresh View", self)
        refresh_btn.triggered.connect(self.refresh_tree_view)
        toolbar.addAction(refresh_btn)

    def create_explore_tab(self):
        """Create the exploration tab."""
        from gui_explore import ExploreWidget
        self.explore_widget = ExploreWidget(self)
        self.explore_widget.exploration_complete.connect(self.on_exploration_complete)
        self.tabs.addTab(self.explore_widget, "Explore Device")

    def create_viewer_tab(self):
        """Create the tree viewer tab."""
        from gui_viewer import TreeViewerWidget
        self.viewer_widget = TreeViewerWidget(self)
        self.tabs.addTab(self.viewer_widget, "View Tree")

    def create_neo4j_tab(self):
        """Create the Neo4j export tab."""
        from gui_neo4j import Neo4jWidget
        self.neo4j_widget = Neo4jWidget(self)
        self.tabs.addTab(self.neo4j_widget, "Neo4j Export")

    def create_logs_tab(self):
        """Create the logs tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_text)

        # Clear logs button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)

        widget.setLayout(layout)
        self.tabs.addTab(widget, "Logs")

    def setup_logging(self):
        """Setup logging to GUI."""
        from gui_logging import QTextEditLogger

        log_handler = QTextEditLogger(self.log_text)
        log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

        # Add handler to root logger
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def open_json_file(self):
        """Open a JSON file containing the command tree."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Command Tree JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                self.current_file = file_path
                self.current_trie = CommandTrie.load_from_file(file_path)

                self.statusBar.showMessage(f"Loaded: {file_path}")
                logger.info(f"Loaded tree with {self.current_trie.total_commands} commands")

                # Update viewer
                self.viewer_widget.load_trie(self.current_trie)

                # Update Neo4j widget
                self.neo4j_widget.set_trie(self.current_trie)

                # Switch to viewer tab
                self.tabs.setCurrentIndex(1)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
                logger.error(f"Failed to load file: {e}", exc_info=True)

    def save_json_file(self):
        """Save the current command tree to a JSON file."""
        if self.current_trie is None:
            QMessageBox.warning(self, "Warning", "No command tree loaded")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Command Tree JSON",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                self.current_trie.save_to_file(file_path)
                self.current_file = file_path
                self.statusBar.showMessage(f"Saved: {file_path}")
                logger.info(f"Saved tree to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")
                logger.error(f"Failed to save file: {e}", exc_info=True)

    def refresh_tree_view(self):
        """Refresh the tree view."""
        if self.current_trie:
            self.viewer_widget.load_trie(self.current_trie)
            self.statusBar.showMessage("View refreshed")

    def on_exploration_complete(self, trie, file_path):
        """Handle completion of exploration."""
        self.current_trie = trie
        self.current_file = file_path

        # Update viewer
        self.viewer_widget.load_trie(trie)

        # Update Neo4j widget
        self.neo4j_widget.set_trie(trie)

        # Show message
        QMessageBox.information(
            self,
            "Exploration Complete",
            f"Successfully explored CLI commands!\n\n"
            f"Total commands: {trie.total_commands}\n"
            f"Saved to: {file_path}"
        )

        # Switch to viewer tab
        self.tabs.setCurrentIndex(1)

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Cisco CLI Explorer",
            "<h2>Cisco CLI Explorer</h2>"
            "<p>A PyATS-based tool for exploring and mapping Cisco CLI command trees.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Depth-first search of CLI commands</li>"
            "<li>Trie data structure for efficient storage</li>"
            "<li>Neo4j graph database integration</li>"
            "<li>Visual tree exploration</li>"
            "</ul>"
            "<p><b>Version:</b> 1.0.0</p>"
            "<p>Built with PyATS and PySide6</p>"
        )


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Cisco CLI Explorer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
