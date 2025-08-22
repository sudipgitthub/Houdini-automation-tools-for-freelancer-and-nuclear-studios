import hou
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import QDateTime
import os
import re
import shutil
import getpass
import subprocess
import sys

try:
    import OpenImageIO as oiio
    HAS_OIIO = True
except ImportError:
    HAS_OIIO = False


def get_folder_owner(path):
    try:
        if os.name == 'nt':
            try:
                import win32security
                sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                return f"{domain}\\{name}"
            except ImportError:
                return getpass.getuser()
            except Exception as e:
                print(f"Error getting Windows owner for {path}: {e}")
                return "Unknown"
        else:
            import pwd
            stat_info = os.stat(path)
            return pwd.getpwuid(stat_info.st_uid).pw_name
    except Exception as e:
        print(f"Error getting owner for {path}: {e}")
        return "Unknown"


class RenderBrowser(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        parent = parent or hou.ui.mainQtWindow()
        super(RenderBrowser, self).__init__(parent)
        self.setWindowTitle("Render Browser")

        # ✅ Normal Windows-style window with Minimize / Maximize / Close
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.WindowMinimizeButtonHint |
                            QtCore.Qt.WindowMaximizeButtonHint |
                            QtCore.Qt.WindowCloseButtonHint)

        self.resize(900, 550)

        # QMainWindow needs a central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # --- Styling ---
        self.setStyleSheet(""" QWidget {
            background-color: #2b2b2b;
            color: #dddddd;
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 8pt;
        } QHeaderView::section {
            background-color: #3c3c3c;
            color: #dddddd;
            padding: 4px;
            border: 1px solid #444;
        } QTableWidget {
            background-color: #2b2b2b;
            gridline-color: #555555;
            alternate-background-color: #3a3a3a;
        } QTableWidget::item:selected {
            background-color: #505F79;
            color: white;
        } QMenu {
            background-color: #2b2b2b;
            color: #dddddd;
            border: 1px solid #444444;
        } QMenu::item:selected {
            background-color: #505F79;
        } QLabel {
            color: #dddddd;
        } QMessageBox {
            background-color: #2b2b2b;
        }""")

        # --- Top path bar ---
        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("Set Render Directory...")
        self.path_edit.setText(self.get_initial_render_path())
        path_layout.addWidget(self.path_edit)

        button_style = """
        QPushButton {
            background-color: #bfbfbf;
            color: #1e1e1e;
            padding: 2px 2px;
            border-radius: 4px;
            font-weight: 400;
        }
        QPushButton:hover { background-color: #555555; }
        QPushButton:pressed { background-color: #222222; }
        """

        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.setStyleSheet(button_style)
        browse_button.clicked.connect(self.browse_render_path)

        set_button = QtWidgets.QPushButton("Set")
        set_button.setStyleSheet(button_style)
        set_button.clicked.connect(self.set_render_path)

        refresh_button = QtWidgets.QPushButton("🔄 Refresh")
        refresh_button.setStyleSheet(button_style)
        refresh_button.clicked.connect(self.populate_render_table)

        path_layout.addWidget(browse_button)
        path_layout.addWidget(set_button)
        path_layout.addWidget(refresh_button)
        main_layout.addLayout(path_layout)

        # --- Render table ---
        self.render_table = QtWidgets.QTableWidget()
        self.render_table.setColumnCount(8)
        self.render_table.setHorizontalHeaderLabels([
            "Preview", "Render Layer", "Frame Range", "Frame No", "Resolution",
            "Version", "Date & Time", "User"
        ])
        self.render_table.horizontalHeader().setStretchLastSection(True)
        self.render_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.render_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.render_table.verticalHeader().setVisible(False)
        self.render_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.render_table.customContextMenuRequested.connect(self.show_render_context_menu)
        self.render_table.cellDoubleClicked.connect(self.handle_render_double_click)

        main_layout.addWidget(self.render_table)

        # Populate after startup
        QtCore.QTimer.singleShot(300, self.populate_render_table)

    def get_initial_render_path(self):
        if hasattr(hou.session, "last_render_path"):
            return os.path.normpath(hou.session.last_render_path)
        return os.path.normpath(os.path.join(hou.getenv("HIP") or "", "render"))

    def set_render_path(self):
        path = os.path.normpath(self.path_edit.text().strip())
        if not os.path.exists(path):
            QtWidgets.QMessageBox.warning(self, "Invalid Path", f"The path does not exist:\n{path}")
            return
        self.path_edit.setText(path)
        hou.session.last_render_path = path
        self.populate_render_table()

    def browse_render_path(self):
        selected = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Render Directory", self.path_edit.text())
        if selected:
            normalized = os.path.normpath(selected)
            self.path_edit.setText(normalized)

    def generate_thumbnail(self, image_path, size=(160, 90)):
        label = QtWidgets.QLabel()
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("padding: 2px; background-color: #222222; color: gray;")
        if not os.path.isfile(image_path):
            label.setText("File not found")
            return label

        ext = os.path.splitext(image_path)[1].lower()
        display_path = image_path

        if ext == ".exr" and HAS_OIIO:
            try:
                import tempfile
                buf = oiio.ImageBuf(image_path)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                display_path = tmp.name
                buf.write(display_path)
            except Exception:
                label.setText("EXR read error")
                return label

        reader = QtGui.QImageReader(display_path)
        reader.setAutoTransform(True)
        image = reader.read()

        if image.isNull():
            label.setText("Unsupported Format")
        else:
            pixmap = QtGui.QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(size[0], size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)

        if ext == ".exr" and HAS_OIIO:
            try:
                os.remove(display_path)
            except:
                pass

        return label

    def populate_render_table(self):
        try:
            self.render_table.setRowCount(0)
            render_dir = self.path_edit.text().strip()
            if not os.path.exists(render_dir):
                return
            version_folders = sorted([f for f in os.listdir(render_dir) if f.lower().startswith('v') and os.path.isdir(os.path.join(render_dir, f))])
            row = 0
            for i, version in enumerate(version_folders):
                version_path = os.path.join(render_dir, version)
                layer_folders = sorted(os.listdir(version_path))
                text_color = QtGui.QColor("#FFFFFF") if i % 2 == 0 else QtGui.QColor("#FFDAB3")
                for layer in layer_folders:
                    layer_path = os.path.join(version_path, layer)
                    if not os.path.isdir(layer_path):
                        continue
                    exr_files = [f for f in os.listdir(layer_path) if os.path.splitext(f)[1].lower() in (".exr", ".jpg", ".jpeg", ".png", ".dpx", ".tif", ".tiff")]
                    if not exr_files:
                        continue
                    exr_files.sort()
                    pattern = re.compile(r"^(.*?)(\d+)\.[^.]+$")
                    matches = [pattern.match(f) for f in exr_files]
                    frame_range = f"{int(matches[0].group(2))}-{int(matches[-1].group(2))}" if matches and all(matches) else f"1-{len(exr_files)}"
                    resolution = "Unknown"
                    try:
                        if HAS_OIIO:
                            img = oiio.ImageInput.open(os.path.join(layer_path, exr_files[0]))
                            if img:
                                spec = img.spec()
                                resolution = f"{spec.width}x{spec.height}"
                                img.close()
                    except Exception:
                        resolution = "Unknown"

                    modified_time = os.path.getmtime(layer_path)
                    datetime_str = QDateTime.fromSecsSinceEpoch(int(modified_time)).toString("yyyy-MM-dd hh:mm")
                    user = get_folder_owner(layer_path)
                    frame_count = str(len(exr_files))
                    self.render_table.insertRow(row)
                    thumb_path = os.path.join(layer_path, exr_files[len(exr_files) // 2])
                    thumb_label = self.generate_thumbnail(thumb_path)
                    self.render_table.setCellWidget(row, 0, thumb_label)
                    row_data = [layer, frame_range, frame_count, resolution, version, datetime_str, user]
                    for col, data in enumerate(row_data):
                        item = QtWidgets.QTableWidgetItem(data)
                        item.setForeground(text_color)
                        item.setData(QtCore.Qt.UserRole, layer_path)
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        if col == 0:
                            item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                        self.render_table.setItem(row, col + 1, item)
                    row += 1

            min_widths = [60, 140, 140, 80, 140, 70, 140, 140]
            for col, width in enumerate(min_widths):
                self.render_table.setColumnWidth(col, width)
                self.render_table.horizontalHeader().setMinimumSectionSize(50)
        except Exception as e:
            print("populate_render_table error:", e)

    def show_render_context_menu(self, pos):
        index = self.render_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.render_table.item(row, 1)
        if not item:
            return
        folder_path = item.data(QtCore.Qt.UserRole)
        if not folder_path or not os.path.exists(folder_path):
            return
        menu = QtWidgets.QMenu()
        menu.addAction("📂 Open Folder", lambda: self.open_folder(folder_path))
        menu.addAction("📋 Copy Path", lambda: QtWidgets.QApplication.clipboard().setText(folder_path))
        menu.addAction("🗑️ Delete", lambda: self.delete_render_folder(row, folder_path))
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 6px;
                padding: 2px;
                color: #ffffff;
            }
            QMenu::item {
                padding: 2px 20px;
                border-radius: 6px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 50);
                color: #ffffff;
            }
        """)
        menu.exec_(self.render_table.viewport().mapToGlobal(pos))

    def handle_render_double_click(self, row, column):
        layer_item = self.render_table.item(row, 1)
        version_item = self.render_table.item(row, 5)
        if not layer_item or not version_item:
            return
        folder = os.path.normpath(os.path.join(self.path_edit.text(), version_item.text(), layer_item.text()))
        if not os.path.exists(folder):
            QtWidgets.QMessageBox.warning(self, "Not Found", f"Folder not found:\n{folder}")
            return
        try:
            extensions = [".exr", ".jpg", ".jpeg", ".png", ".dpx", ".tif", ".tiff"]
            files = sorted(f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in extensions)
            pattern = re.compile(r"(.*?)(\d+)\.(exr|jpg|jpeg|png|dpx|tif|tiff)$", re.IGNORECASE)
            matches = [pattern.match(f) for f in files if pattern.match(f)]
            if matches:
                base, start = matches[0].group(1), int(matches[0].group(2))
                end = int(matches[-1].group(2))
                ext = matches[0].group(3).lower()
                padding = len(matches[0].group(2))
                sequence = os.path.join(folder, f"{base}$F{padding}.{ext}")
                try:
                    subprocess.Popen(["mplay", "-f", str(start), str(end), "1", sequence])
                    return
                except FileNotFoundError:
                    QtWidgets.QMessageBox.warning(self, "MPlay Not Found", "MPlay is not installed or not in PATH.")
            mp4s = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".mp4")]
            if mp4s:
                if os.name == 'nt':
                    os.startfile(mp4s[0])
                elif sys.platform == 'darwin':
                    subprocess.Popen(["open", mp4s[0]])
                else:
                    subprocess.Popen(["xdg-open", mp4s[0]])
                return
            self.open_folder(folder)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def delete_render_folder(self, row, path):
        confirm = QtWidgets.QMessageBox.question(self, "Confirm Delete", f"Delete:\n{path}?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                shutil.rmtree(path)
                self.render_table.removeRow(row)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Delete Failed", str(e))

    def open_folder(self, folder):
        if os.name == 'nt':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])


# -------------------------------
# Launch Helper
# -------------------------------
_render_browser_instance = None

def show_render_browser():
    global _render_browser_instance
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    if _render_browser_instance is None:
        _render_browser_instance = RenderBrowser()

        def reset_instance():
            global _render_browser_instance
            _render_browser_instance = None

        # reset when closed/destroyed
        _render_browser_instance.destroyed.connect(reset_instance)

    _render_browser_instance.show()
    _render_browser_instance.raise_()
    _render_browser_instance.activateWindow()

    if not QtWidgets.QApplication.instance():
        app.exec_()


# -------------------------------
# Run
# -------------------------------
show_render_browser()
