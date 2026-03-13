"""Administrative dialogs for user management."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.access_control import AccessController
from core.config import Config
from core.database import AccessLog, User, get_session
from core.platform_utils import open_in_file_manager
from core.qr_handler import QRHandler

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class QRPreviewDialog(QDialog):
    """Preview dialog displayed after generating a QR."""

    def __init__(self, qr_path: Path, user_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QR generado")
        self.resize(450, 550)

        layout = QVBoxLayout(self)

        title = QLabel(f"QR para: {user_name}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #ff6b35; padding: 10px;"
        )
        layout.addWidget(title)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(qr_path))
        qr_label.setPixmap(
            pixmap.scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        qr_label.setStyleSheet(
            "background-color: white; padding: 20px; border-radius: 8px;"
        )
        layout.addWidget(qr_label)

        path_label = QLabel(f"Guardado en:\n{qr_path}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #c0c0c0; padding: 10px;")
        layout.addWidget(path_label)

        buttons = QHBoxLayout()

        open_button = QPushButton("Abrir carpeta")
        open_button.clicked.connect(lambda: self.open_folder(qr_path))
        buttons.addWidget(open_button)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("start_button")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)

        layout.addLayout(buttons)

    def open_folder(self, qr_path: Path) -> None:
        if not open_in_file_manager(qr_path):
            QMessageBox.warning(self, "Error", "No se pudo abrir la carpeta del QR.")


class AdminDialog(QDialog):
    """Administrative panel used to manage users and logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{Config.ORGANIZATION_NAME} | Administracion - Usuarios")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        brand_label = QLabel(
            f"{Config.ORGANIZATION_NAME} | Official Administration Panel"
        )
        brand_label.setObjectName("brand_label")
        layout.addWidget(brand_label)

        create_group = QGroupBox("Crear nuevo usuario")
        create_layout = QVBoxLayout(create_group)

        input_layout = QHBoxLayout()
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Nombre completo")
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("email@example.com")
        input_layout.addWidget(QLabel("Nombre:"))
        input_layout.addWidget(self.input_name)
        input_layout.addWidget(QLabel("Email:"))
        input_layout.addWidget(self.input_email)
        create_layout.addLayout(input_layout)

        self.btn_create = QPushButton("Crear usuario + generar QR")
        self.btn_create.setObjectName("start_button")
        self.btn_create.clicked.connect(self.create_user_with_qr)
        create_layout.addWidget(self.btn_create)

        layout.addWidget(create_group)

        users_group = QGroupBox("Usuarios registrados")
        users_layout = QVBoxLayout(users_group)

        self.user_list = QListWidget()
        self.user_list.setAlternatingRowColors(True)
        users_layout.addWidget(self.user_list)

        button_row = QHBoxLayout()

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.load_users)
        button_row.addWidget(self.btn_refresh)

        self.btn_toggle = QPushButton("Activar/Desactivar")
        self.btn_toggle.clicked.connect(self.toggle_user_active)
        button_row.addWidget(self.btn_toggle)

        self.btn_gen_qr = QPushButton("Regenerar QR")
        self.btn_gen_qr.clicked.connect(self.generate_selected_qr)
        button_row.addWidget(self.btn_gen_qr)

        self.btn_delete_log = QPushButton("Eliminar registro")
        self.btn_delete_log.clicked.connect(self.delete_access_log)
        button_row.addWidget(self.btn_delete_log)

        self.btn_open_qr_folder = QPushButton("Abrir carpeta QR")
        self.btn_open_qr_folder.clicked.connect(self.open_qr_folder)
        button_row.addWidget(self.btn_open_qr_folder)

        users_layout.addLayout(button_row)
        layout.addWidget(users_group)

        self.load_users()

    def load_users(self) -> None:
        self.user_list.clear()
        session = get_session()
        try:
            users = session.query(User).order_by(User.created_at.desc()).all()
            for user in users:
                status = "Activo" if user.is_active else "Inactivo"
                label = f"{user.id} | {user.name} <{user.email}> - {status}"
                item = QListWidgetItem(label)
                item.setForeground(Qt.white if user.is_active else Qt.gray)
                self.user_list.addItem(item)
        finally:
            session.close()

    def _selected_user_id(self):
        item = self.user_list.currentItem()
        if not item:
            return None

        try:
            return int(item.text().split("|", 1)[0].strip())
        except (TypeError, ValueError):
            return None

    def _build_payload(self, user: User):
        return QRHandler.build_payload(
            user_uuid=user.uuid,
            name=user.name,
            email=user.email,
        )

    def _validate_user_form(self, name: str, email: str) -> Optional[str]:
        if not name:
            return "Ingresa un nombre."
        if not email:
            return "Ingresa un email."
        if not EMAIL_RE.match(email):
            return "El email no tiene un formato valido."
        return None

    @Slot()
    def create_user_with_qr(self) -> None:
        name = self.input_name.text().strip()
        email = self.input_email.text().strip().lower()

        error_message = self._validate_user_form(name, email)
        if error_message:
            QMessageBox.warning(self, "Datos invalidos", error_message)
            return

        session = get_session()
        try:
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                QMessageBox.warning(
                    self,
                    "Email duplicado",
                    "Ya existe un usuario registrado con ese email.",
                )
                return

            user = User(uuid=str(uuid.uuid4()), name=name, email=email, is_active=True)
            session.add(user)
            session.flush()

            qr_path, _ = QRHandler.generate_qr_file(
                self._build_payload(user),
                out_dir=Path(Config.QR_OUTPUT_DIR),
                filename_prefix=f"qr_{name}",
            )

            session.commit()
            AccessController.invalidate_user_cache(user.uuid)

            self.input_name.clear()
            self.input_email.clear()
            self.load_users()

            QRPreviewDialog(qr_path, name, self).exec()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo crear el usuario:\n{exc}")
        finally:
            session.close()

    @Slot()
    def toggle_user_active(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.warning(
                self, "Selecciona un usuario", "Selecciona un usuario de la lista."
            )
            return

        session = get_session()
        try:
            user = session.get(User, user_id)
            if not user:
                QMessageBox.warning(self, "Error", "Usuario no encontrado.")
                return

            user.is_active = not bool(user.is_active)
            session.add(user)
            session.commit()
            AccessController.invalidate_user_cache(user.uuid)

            self.load_users()
            status = "activado" if user.is_active else "desactivado"
            QMessageBox.information(
                self, "Estado actualizado", f"Usuario {user.name} {status}."
            )
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Error al cambiar estado:\n{exc}")
        finally:
            session.close()

    @Slot()
    def generate_selected_qr(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.warning(
                self, "Selecciona un usuario", "Selecciona un usuario de la lista."
            )
            return

        session = get_session()
        try:
            user = session.get(User, user_id)
            if not user:
                QMessageBox.warning(self, "Error", "Usuario no encontrado.")
                return

            qr_path, _ = QRHandler.generate_qr_file(
                self._build_payload(user),
                out_dir=Path(Config.QR_OUTPUT_DIR),
                filename_prefix=f"qr_{user.name}",
            )

            QRPreviewDialog(qr_path, user.name, self).exec()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo generar el QR:\n{exc}")
        finally:
            session.close()

    @Slot()
    def delete_access_log(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            QMessageBox.warning(
                self, "Selecciona un usuario", "Selecciona un usuario de la lista."
            )
            return

        session = get_session()
        try:
            user = session.get(User, user_id)
            if not user:
                QMessageBox.warning(self, "Error", "Usuario no encontrado.")
                return

            logs = (
                session.query(AccessLog)
                .filter_by(user_uuid=user.uuid)
                .order_by(AccessLog.timestamp.desc())
                .limit(10)
                .all()
            )

            if not logs:
                QMessageBox.information(
                    self, "Sin registros", f"No hay registros para {user.name}."
                )
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Registros de {user.name}")
            dialog.resize(500, 300)

            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("Selecciona el registro a eliminar:"))

            log_list = QListWidget()
            for log in logs:
                time_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                log_list.addItem(
                    f"ID: {log.id} | {log.access_type.upper()} | {time_str}"
                )
            layout.addWidget(log_list)

            actions = QHBoxLayout()
            delete_button = QPushButton("Eliminar")
            delete_button.setObjectName("start_button")
            cancel_button = QPushButton("Cancelar")
            actions.addWidget(delete_button)
            actions.addWidget(cancel_button)
            layout.addLayout(actions)

            cancel_button.clicked.connect(dialog.reject)

            def delete_selected() -> None:
                selected = log_list.currentItem()
                if not selected:
                    QMessageBox.warning(
                        dialog, "Selecciona un registro", "Selecciona un registro."
                    )
                    return

                log_id = int(selected.text().split("|")[0].replace("ID:", "").strip())
                reply = QMessageBox.question(
                    dialog,
                    "Confirmar",
                    "Eliminar este registro?",
                    QMessageBox.Yes | QMessageBox.No,
                )

                if reply != QMessageBox.Yes:
                    return

                log_to_delete = session.get(AccessLog, log_id)
                if log_to_delete:
                    session.delete(log_to_delete)
                    session.commit()
                    QMessageBox.information(
                        dialog, "Exito", "Registro eliminado correctamente."
                    )
                    dialog.accept()

            delete_button.clicked.connect(delete_selected)
            dialog.exec()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Error al eliminar registro:\n{exc}")
        finally:
            session.close()

    @Slot()
    def open_qr_folder(self) -> None:
        folder = Path(Config.QR_OUTPUT_DIR)
        folder.mkdir(parents=True, exist_ok=True)

        if not open_in_file_manager(folder):
            QMessageBox.warning(self, "Error", "No se pudo abrir la carpeta de QRs.")
