"""
Logging handler for GUI QTextEdit widget.
"""
import logging
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QTextCursor, QColor


class QTextEditLogger(logging.Handler, QObject):
    """Logging handler that writes to a QTextEdit widget."""

    append_text = Signal(str)

    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        QObject.__init__(self)

        self.text_widget = text_widget
        self.append_text.connect(self.text_widget.append)

    def emit(self, record):
        """Emit a log record."""
        try:
            msg = self.format(record)
            self.append_text.emit(msg)

            # Auto-scroll to bottom
            cursor = self.text_widget.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_widget.setTextCursor(cursor)

        except Exception:
            self.handleError(record)
