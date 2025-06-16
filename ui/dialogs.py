from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QApplication, QMessageBox, QFileDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class ConfigOutputDialog(QDialog):
    def __init__(self, text_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generated config.h Content")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text_content)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 10))
        layout.addWidget(self.text_edit)
        button_layout = QHBoxLayout()
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)
        self.save_button = QPushButton("Save to File...")
        self.save_button.clicked.connect(self.save_config_to_file)
        button_layout.addWidget(self.save_button)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "Copied", "Config copied.")
        self.accept()

    def save_config_to_file(self):
        content = self.text_edit.toPlainText()
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getSaveFileName(self, "Save Config File", "config.h",
                                                  "Header Files (*.h);;All Files (*)", options=options)
        if filePath:
            try:
                with open(filePath, 'w') as f: f.write(content)
                QMessageBox.information(self, "Saved", f"Config saved to {filePath}")
                self.accept()
            except Exception as e: QMessageBox.critical(self, "Save Error", str(e))