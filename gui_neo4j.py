"""
Neo4j export widget for the GUI.
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGroupBox, QFormLayout, QCheckBox, QTextEdit,
    QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont


logger = logging.getLogger(__name__)


class Neo4jExportThread(QThread):
    """Thread for exporting to Neo4j."""

    progress = Signal(str)
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, trie, uri, username, password, database, clear_existing):
        super().__init__()
        self.trie = trie
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.clear_existing = clear_existing

    def run(self):
        """Run the export."""
        try:
            from load_to_neo4j import Neo4jLoader

            self.progress.emit("Connecting to Neo4j...")

            loader = Neo4jLoader(
                uri=self.uri,
                username=self.username,
                password=self.password,
                database=self.database
            )

            # Verify connection
            if not loader.verify_connection():
                self.error.emit("Failed to connect to Neo4j. Please check connection settings.")
                loader.close()
                return

            self.progress.emit("Loading data into Neo4j...")

            loader.load_from_trie(self.trie, clear_existing=self.clear_existing)

            nodes_created = loader.nodes_created
            relationships_created = loader.relationships_created

            loader.close()

            self.progress.emit("Export complete!")
            self.finished.emit(nodes_created, relationships_created)

        except ImportError as e:
            self.error.emit("Neo4j driver not installed. Please install: pip install neo4j>=5.0.0")
        except Exception as e:
            logger.error(f"Neo4j export failed: {e}", exc_info=True)
            self.error.emit(str(e))


class Neo4jWidget(QWidget):
    """Widget for Neo4j export configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_trie = None
        self.export_thread = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("<h2>Export to Neo4j Graph Database</h2>")
        layout.addWidget(title)

        # Connection settings group
        conn_group = QGroupBox("Neo4j Connection Settings")
        conn_layout = QFormLayout()

        self.uri_edit = QLineEdit()
        self.uri_edit.setText("bolt://localhost:7687")
        conn_layout.addRow("URI:", self.uri_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setText("neo4j")
        conn_layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter password...")
        conn_layout.addRow("Password:", self.password_edit)

        self.database_edit = QLineEdit()
        self.database_edit.setText("neo4j")
        conn_layout.addRow("Database:", self.database_edit)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Options group
        options_group = QGroupBox("Export Options")
        options_layout = QVBoxLayout()

        self.clear_existing_check = QCheckBox("Clear existing data before import")
        self.clear_existing_check.setChecked(True)
        options_layout.addWidget(self.clear_existing_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Sample queries section
        queries_label = QLabel("<b>Sample Cypher Queries (use in Neo4j Browser)</b>")
        layout.addWidget(queries_label)

        self.queries_text = QTextEdit()
        self.queries_text.setReadOnly(True)
        self.queries_text.setFont(QFont("Courier", 9))
        self.queries_text.setMaximumHeight(200)
        self.queries_text.setPlainText(self.get_sample_queries())
        layout.addWidget(self.queries_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_conn_btn)

        self.export_btn = QPushButton("Export to Neo4j")
        self.export_btn.clicked.connect(self.start_export)
        self.export_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Add stretch to push everything to the top
        layout.addStretch()

        self.setLayout(layout)

    def set_trie(self, trie):
        """Set the trie to export."""
        self.current_trie = trie
        if trie:
            self.status_label.setText(f"Ready to export {trie.total_commands} commands")
            self.export_btn.setEnabled(True)
        else:
            self.status_label.setText("No command tree loaded")
            self.export_btn.setEnabled(False)

    def test_connection(self):
        """Test Neo4j connection."""
        try:
            from load_to_neo4j import Neo4jLoader

            uri = self.uri_edit.text().strip()
            username = self.username_edit.text().strip()
            password = self.password_edit.text()
            database = self.database_edit.text().strip()

            if not password:
                QMessageBox.warning(self, "Missing Password", "Please enter a password")
                return

            self.status_label.setText("Testing connection...")
            QApplication.processEvents()

            loader = Neo4jLoader(uri, username, password, database)

            if loader.verify_connection():
                QMessageBox.information(
                    self,
                    "Connection Successful",
                    f"Successfully connected to Neo4j at {uri}"
                )
                self.status_label.setText("Connection successful!")
            else:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    "Failed to connect to Neo4j. Please check your settings."
                )
                self.status_label.setText("Connection failed")

            loader.close()

        except ImportError:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "Neo4j driver not installed.\n\nPlease install: pip install neo4j>=5.0.0"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error testing connection:\n\n{str(e)}"
            )
            self.status_label.setText("Error testing connection")

    def start_export(self):
        """Start the Neo4j export."""
        if self.current_trie is None:
            QMessageBox.warning(self, "No Data", "No command tree loaded. Please explore a device first.")
            return

        # Validate inputs
        uri = self.uri_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        database = self.database_edit.text().strip()

        if not uri or not username or not password or not database:
            QMessageBox.warning(self, "Missing Information", "Please fill in all connection fields")
            return

        # Confirm if clearing existing data
        if self.clear_existing_check.isChecked():
            reply = QMessageBox.question(
                self,
                "Confirm Clear",
                "This will delete all existing Command nodes in the database. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Disable export button
        self.export_btn.setEnabled(False)
        self.test_conn_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_label.setText("Exporting...")

        # Start export thread
        self.export_thread = Neo4jExportThread(
            trie=self.current_trie,
            uri=uri,
            username=username,
            password=password,
            database=database,
            clear_existing=self.clear_existing_check.isChecked()
        )

        self.export_thread.progress.connect(self.on_progress)
        self.export_thread.finished.connect(self.on_finished)
        self.export_thread.error.connect(self.on_error)

        self.export_thread.start()

    def on_progress(self, message):
        """Handle progress update."""
        self.status_label.setText(message)

    def on_finished(self, nodes_created, relationships_created):
        """Handle export completion."""
        self.progress_bar.hide()
        self.export_btn.setEnabled(True)
        self.test_conn_btn.setEnabled(True)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Successfully exported to Neo4j!\n\n"
            f"Nodes created: {nodes_created}\n"
            f"Relationships created: {relationships_created}\n\n"
            f"You can now browse the graph at:\n"
            f"http://localhost:7474"
        )

        self.status_label.setText(f"Export complete! Nodes: {nodes_created}, Relationships: {relationships_created}")

    def on_error(self, error_msg):
        """Handle export error."""
        self.progress_bar.hide()
        self.export_btn.setEnabled(True)
        self.test_conn_btn.setEnabled(True)
        self.status_label.setText("Export failed")

        QMessageBox.critical(self, "Export Error", f"Export failed:\n\n{error_msg}")

    def get_sample_queries(self):
        """Get sample Cypher queries."""
        return """-- Count all commands
MATCH (c:Command) RETURN count(c) as total_commands

-- Find complete commands
MATCH (c:Command {is_end_of_command: true})
RETURN c.path, c.description ORDER BY c.path

-- Search for 'interface' commands
MATCH (c:Command)
WHERE c.token CONTAINS 'interface'
RETURN c.path, c.description

-- Get 'show' command subtree (3 levels)
MATCH path = (root:Command {token: 'show'})-[:HAS_CHILD*0..3]->(child)
RETURN path

-- Find commands with most children
MATCH (parent:Command)-[:HAS_CHILD]->(child)
WITH parent, count(child) as child_count
RETURN parent.path, child_count
ORDER BY child_count DESC LIMIT 10
"""


# Import QApplication for processEvents
from PySide6.QtWidgets import QApplication
