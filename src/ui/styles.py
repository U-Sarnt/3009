# src/ui/styles.py
"""
Estilos de la aplicación - Tema Negro/Naranja/Gris
"""

MAIN_STYLE = """
/* ============================================
   CONFIGURACIÓN GLOBAL
   ============================================ */
QMainWindow {
    background-color: #1a1a1a;
}

QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 11pt;
}

/* ============================================
   BOTONES
   ============================================ */
QPushButton {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border: 2px solid #404040;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    min-height: 35px;
}

QPushButton:hover {
    background-color: #ff6b35;
    border: 2px solid #ff8555;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #e55a25;
    border: 2px solid #ff6b35;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #606060;
    border: 2px solid #303030;
}

QPushButton#start_button {
    background-color: #ff6b35;
    border: 2px solid #ff8555;
    color: #ffffff;
}

QPushButton#start_button:hover {
    background-color: #ff8555;
    border: 2px solid #ffa075;
}

QPushButton#start_button:pressed {
    background-color: #e55a25;
}

/* ============================================
   LABELS
   ============================================ */
QLabel {
    background-color: transparent;
    color: #e0e0e0;
}

QLabel#camera_label {
    background-color: #0d0d0d;
    border: 3px solid #404040;
    border-radius: 8px;
    color: #808080;
    font-size: 14pt;
}

QLabel#status_label {
    background-color: #2a2a2a;
    border: 2px solid #ff6b35;
    border-radius: 6px;
    padding: 12px;
    font-size: 13pt;
    font-weight: bold;
    color: #e0e0e0;
}

QLabel#status_label[status="success"] {
    background-color: #1a3a1a;
    border: 2px solid #4caf50;
    color: #6fbf73;
}

QLabel#status_label[status="error"] {
    background-color: #3a1a1a;
    border: 2px solid #f44336;
    color: #ef5350;
}

QLabel#status_label[status="ready"] {
    background-color: #2a2a2a;
    border: 2px solid #ff6b35;
    color: #ff8555;
}

QLabel#last_access_label {
    background-color: #0d0d0d;
    border: 2px solid #404040;
    border-left: 4px solid #ff6b35;
    border-radius: 6px;
    padding: 12px;
    font-size: 12pt;
    color: #c0c0c0;
}

QLabel#brand_label {
    background-color: #111111;
    border: 1px solid #404040;
    border-left: 4px solid #ff6b35;
    border-radius: 6px;
    padding: 10px;
    color: #ffb08a;
    font-size: 10pt;
    font-weight: bold;
}

/* ============================================
   TABLA
   ============================================ */
QTableWidget {
    background-color: #0d0d0d;
    alternate-background-color: #1a1a1a;
    border: 2px solid #404040;
    border-radius: 6px;
    gridline-color: #303030;
    color: #e0e0e0;
    selection-background-color: #ff6b35;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #303030;
}

QTableWidget::item:selected {
    background-color: #ff6b35;
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: #2a2a2a;
}

QHeaderView::section {
    background-color: #2a2a2a;
    color: #ff6b35;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #ff6b35;
    border-right: 1px solid #404040;
    font-weight: bold;
    font-size: 11pt;
}

QHeaderView::section:hover {
    background-color: #353535;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #404040;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #ff6b35;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QDialog {
    background-color: #1a1a1a;
}

QLineEdit {
    background-color: #0d0d0d;
    border: 2px solid #404040;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
    selection-background-color: #ff6b35;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 2px solid #ff6b35;
}

QLineEdit:disabled {
    background-color: #1a1a1a;
    color: #606060;
    border: 2px solid #303030;
}

QMessageBox {
    background-color: #1a1a1a;
}

QMessageBox QLabel {
    color: #e0e0e0;
    min-width: 300px;
}

QMessageBox QPushButton {
    min-width: 80px;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #404040;
    border-radius: 4px;
    background-color: #0d0d0d;
}

QCheckBox::indicator:hover {
    border: 2px solid #ff6b35;
}

QCheckBox::indicator:checked {
    background-color: #ff6b35;
    border: 2px solid #ff8555;
}

QCheckBox::indicator:checked:hover {
    background-color: #ff8555;
}
"""
