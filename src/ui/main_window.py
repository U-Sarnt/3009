"""Main application window."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.access_control import AccessController
from core.camera import CameraThread
from core.config import Config
from ui.admin_dialog import AdminDialog
from ui.styles import MAIN_STYLE


class MainWindow(QMainWindow):
    """Main dashboard shown to the operator."""

    def __init__(self):
        super().__init__()
        self.camera_thread = None
        self.access_controller = AccessController()
        self.update_timer = QTimer()

        self.setStyleSheet(MAIN_STYLE)
        self.setup_ui()

        self.update_timer.timeout.connect(self.update_recent_logs)
        self.update_timer.start(5000)

    def setup_ui(self) -> None:
        self.setWindowTitle(Config.PROJECT_NAME)
        self.setMinimumSize(960, 620)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.camera_label = QLabel()
        self.camera_label.setObjectName("camera_label")
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setText("Camara apagada")
        left_layout.addWidget(self.camera_label)

        button_row = QHBoxLayout()

        self.start_button = QPushButton("Iniciar camara")
        self.start_button.clicked.connect(self.start_camera)
        button_row.addWidget(self.start_button)

        self.stop_button = QPushButton("Detener camara")
        self.stop_button.clicked.connect(self.stop_camera)
        self.stop_button.setEnabled(False)
        button_row.addWidget(self.stop_button)

        self.admin_button = QPushButton("Administrar")
        self.admin_button.clicked.connect(self.open_admin)
        button_row.addWidget(self.admin_button)

        left_layout.addLayout(button_row)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.brand_label = QLabel(f"{Config.ORGANIZATION_NAME}\nOfficial Project / Proyecto Oficial")
        self.brand_label.setObjectName("brand_label")
        right_layout.addWidget(self.brand_label)

        self.status_label = QLabel("Sistema listo")
        self.status_label.setObjectName("status_label")
        self.status_label.setProperty("status", "ready")
        right_layout.addWidget(self.status_label)

        self.last_access_label = QLabel("Sin accesos recientes")
        self.last_access_label.setObjectName("last_access_label")
        right_layout.addWidget(self.last_access_label)

        self.summary_label = QLabel("Cargando resumen...")
        self.summary_label.setObjectName("last_access_label")
        right_layout.addWidget(self.summary_label)

        right_layout.addWidget(QLabel("Registros recientes:"))

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["Usuario", "Tipo", "Hora"])
        self.log_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.log_table)

        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel, 1)

        self.update_recent_logs()

    def _apply_status(self, text: str, status: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("status", status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    @Slot()
    def start_camera(self) -> None:
        if self.camera_thread is not None:
            return

        try:
            self.camera_thread = CameraThread(camera_index=Config.CAMERA_INDEX)
            self.camera_thread.frame_ready.connect(self.update_frame)
            self.camera_thread.qr_detected.connect(self.process_qr)
            self.camera_thread.error_occurred.connect(self.show_error)
            self.camera_thread.start()

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self._apply_status("Camara activa - esperando QR...", "ready")
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"No se pudo iniciar la camara: {exc}")
            self.camera_thread = None

    @Slot()
    def stop_camera(self) -> None:
        if self.camera_thread:
            self.camera_thread.stop()
            if not self.camera_thread.wait(5000):
                QMessageBox.warning(self, "Advertencia", "La camara tardo en detenerse.")
            self.camera_thread = None

        self.camera_label.clear()
        self.camera_label.setText("Camara apagada")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._apply_status("Sistema detenido", "ready")

    @Slot(QImage)
    def update_frame(self, image: QImage) -> None:
        if image and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(
                self.camera_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.camera_label.setPixmap(scaled)

    @Slot(str)
    def process_qr(self, qr_data: str) -> None:
        result = self.access_controller.process_qr_code(qr_data)

        if result["success"]:
            self._apply_status(result["message"], "success")
            access_info = f"{result['user']} - {result['access_type'].upper()}"
            timestamp = datetime.fromisoformat(result["timestamp"]).strftime("%H:%M:%S")
            self.last_access_label.setText(f"Ultimo: {access_info} a las {timestamp}")
        else:
            self._apply_status(result["message"], "error")

        self.update_recent_logs()

    @Slot()
    def update_recent_logs(self) -> None:
        try:
            stats = self.access_controller.get_dashboard_stats()
            self.summary_label.setText(
                f"Usuarios activos: {stats['active_users']}/{stats['total_users']} | "
                f"Accesos registrados: {stats['total_logs']}"
            )

            logs = self.access_controller.get_recent_logs(Config.DEFAULT_RECENT_LOG_LIMIT)
            self.log_table.setRowCount(len(logs))

            for index, log in enumerate(logs):
                self.log_table.setItem(index, 0, QTableWidgetItem(log["user"]))
                self.log_table.setItem(index, 1, QTableWidgetItem(log["access_type"].upper()))
                self.log_table.setItem(
                    index,
                    2,
                    QTableWidgetItem(log["timestamp"].strftime("%H:%M:%S")),
                )
        except Exception as exc:
            self.summary_label.setText("No se pudo cargar el resumen")
            print(f"Error actualizando registros: {exc}")

    @Slot()
    def open_admin(self) -> None:
        AdminDialog(self).exec()
        self.update_recent_logs()

    @Slot(str)
    def show_error(self, error_message: str) -> None:
        QMessageBox.critical(self, "Error", error_message)
        self._apply_status(error_message, "error")
        self.stop_camera()

    def closeEvent(self, event) -> None:
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None

        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait(5000)
            self.camera_thread = None

        event.accept()
