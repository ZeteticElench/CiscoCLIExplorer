"""
Tree viewer widget for the GUI.
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QTextEdit, QSplitter,
    QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from trie import CommandTrie, TrieNode


logger = logging.getLogger(__name__)


class TreeViewerWidget(QWidget):
    """Widget for viewing and searching the command tree."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_trie = None
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("<h2>Command Tree Viewer</h2>")
        layout.addWidget(title)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter command or keyword...")
        self.search_edit.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # Splitter for tree and details
        splitter = QSplitter(Qt.Horizontal)

        # Tree widget
        tree_widget = QWidget()
        tree_layout = QVBoxLayout()

        tree_label = QLabel("<b>Command Tree</b>")
        tree_layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Command", "Description"])
        self.tree.setColumnWidth(0, 300)
        self.tree.itemClicked.connect(self.on_item_clicked)
        tree_layout.addWidget(self.tree)

        tree_widget.setLayout(tree_layout)
        splitter.addWidget(tree_widget)

        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout()

        details_label = QLabel("<b>Command Details</b>")
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier", 10))
        details_layout.addWidget(self.details_text)

        details_widget.setLayout(details_layout)
        splitter.addWidget(details_widget)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()

        self.total_commands_label = QLabel("Total Commands: 0")
        stats_layout.addWidget(self.total_commands_label)

        self.max_depth_label = QLabel("Max Depth: 0")
        stats_layout.addWidget(self.max_depth_label)

        self.total_nodes_label = QLabel("Total Nodes: 0")
        stats_layout.addWidget(self.total_nodes_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Buttons
        button_layout = QHBoxLayout()

        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.tree.expandAll)
        button_layout.addWidget(expand_all_btn)

        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.tree.collapseAll)
        button_layout.addWidget(collapse_all_btn)

        export_text_btn = QPushButton("Export to Text")
        export_text_btn.clicked.connect(self.export_to_text)
        button_layout.addWidget(export_text_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_trie(self, trie: CommandTrie):
        """Load a trie into the viewer."""
        self.current_trie = trie
        self.tree.clear()

        if trie is None:
            return

        # Build tree widget
        self.build_tree(trie.root, None)

        # Update statistics
        self.update_statistics()

        # Expand first level
        self.tree.expandToDepth(0)

    def build_tree(self, node: TrieNode, parent_item: QTreeWidgetItem):
        """Recursively build the tree widget."""
        if node.token == "ROOT":
            # Don't show root node
            for child in sorted(node.children.values(), key=lambda x: x.token):
                self.build_tree(child, None)
            return

        # Create tree item
        if parent_item is None:
            item = QTreeWidgetItem(self.tree)
        else:
            item = QTreeWidgetItem(parent_item)

        item.setText(0, node.token)
        item.setText(1, node.description)

        # Store node reference
        item.setData(0, Qt.UserRole, node)

        # Add marker for complete commands
        if node.is_end_of_command:
            item.setText(0, f"{node.token} ✓")
            item.setForeground(0, Qt.darkGreen)

        # Recursively add children
        for child in sorted(node.children.values(), key=lambda x: x.token):
            self.build_tree(child, item)

    def update_statistics(self):
        """Update the statistics display."""
        if self.current_trie is None:
            return

        total_commands = self.current_trie.total_commands
        max_depth = self.calculate_max_depth(self.current_trie.root)
        total_nodes = self.count_nodes(self.current_trie.root)

        self.total_commands_label.setText(f"Total Commands: {total_commands}")
        self.max_depth_label.setText(f"Max Depth: {max_depth}")
        self.total_nodes_label.setText(f"Total Nodes: {total_nodes}")

    def calculate_max_depth(self, node: TrieNode, depth: int = 0) -> int:
        """Calculate maximum depth."""
        if not node.children:
            return depth
        return max(self.calculate_max_depth(child, depth + 1)
                  for child in node.children.values())

    def count_nodes(self, node: TrieNode) -> int:
        """Count total nodes."""
        count = 1
        for child in node.children.values():
            count += self.count_nodes(child)
        return count

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        node = item.data(0, Qt.UserRole)
        if node is None:
            return

        # Build full path
        path = []
        current_item = item
        while current_item is not None:
            current_node = current_item.data(0, Qt.UserRole)
            if current_node and current_node.token != "ROOT":
                path.insert(0, current_node.token.replace(" ✓", ""))
            current_item = current_item.parent()

        # Display details
        details = f"<h3>{node.token}</h3>\n"
        details += f"<b>Full Path:</b> {' '.join(path)}\n\n"
        details += f"<b>Description:</b> {node.description}\n\n"
        details += f"<b>Complete Command:</b> {'Yes' if node.is_end_of_command else 'No'}\n"
        details += f"<b>Children:</b> {len(node.children)}\n\n"

        if node.children:
            details += "<b>Available Sub-commands:</b>\n"
            for token, child in sorted(node.children.items()):
                details += f"  • {token}"
                if child.description:
                    details += f" - {child.description}"
                details += "\n"

        self.details_text.setHtml(details.replace("\n", "<br>"))

    def on_search(self, text: str):
        """Handle search text change."""
        if not text:
            # Show all items
            self.show_all_items()

    def perform_search(self):
        """Perform search."""
        search_text = self.search_edit.text().strip().lower()
        if not search_text:
            return

        # Hide all items first
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item.setHidden(True)
            iterator += 1

        # Show matching items and their parents
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            node = item.data(0, Qt.UserRole)

            if node:
                # Check if token or description matches
                if (search_text in node.token.lower() or
                    search_text in node.description.lower()):
                    # Show this item and all parents
                    current = item
                    while current:
                        current.setHidden(False)
                        current = current.parent()

            iterator += 1

        # Expand matched items
        self.tree.expandAll()

    def show_all_items(self):
        """Show all tree items."""
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            item.setHidden(False)
            iterator += 1

    def export_to_text(self):
        """Export tree to text file."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        if self.current_trie is None:
            QMessageBox.warning(self, "No Data", "No command tree loaded")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Text",
            "commands.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    self.write_tree_text(self.current_trie.root, f)

                QMessageBox.information(self, "Success", f"Exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def write_tree_text(self, node: TrieNode, file, path=None, indent=0):
        """Write tree to text file recursively."""
        if path is None:
            path = []

        if node.token != "ROOT":
            path = path + [node.token]
            line = "  " * indent + node.token
            if node.description:
                line += f" - {node.description}"
            if node.is_end_of_command:
                line += " [COMPLETE]"
            file.write(line + "\n")

        for child in sorted(node.children.values(), key=lambda x: x.token):
            self.write_tree_text(child, file, path, indent + 1)
