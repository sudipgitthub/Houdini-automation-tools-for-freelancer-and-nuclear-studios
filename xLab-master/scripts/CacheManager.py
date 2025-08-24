
import os
import sys
import shutil
import subprocess
from functools import partial
import hou

from PySide2 import QtWidgets, QtCore, QtGui


class CacheBrowser(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CacheBrowser, self).__init__(parent)
        self.setWindowTitle("Cache Browser")

        # ✅ Normal Windows-style window with Minimize / Maximize / Close
        self.setWindowFlags(QtCore.Qt.Window |
                            QtCore.Qt.WindowMinimizeButtonHint |
                            QtCore.Qt.WindowMaximizeButtonHint |
                            QtCore.Qt.WindowCloseButtonHint)

        self.resize(900, 550)

        # --- Main Layout ---
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)

        # --- Path Selector ---
        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setReadOnly(True)

        set_path_btn = QtWidgets.QPushButton("Set Folder")
        set_path_btn.setFixedWidth(100)
        set_path_btn.clicked.connect(self.set_cache_dir)

        path_layout.addWidget(QtWidgets.QLabel("Cache Path:"))
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(set_path_btn)
        main_layout.addLayout(path_layout)

        # --- Top Bar (Search + Refresh) ---
        top_layout = QtWidgets.QHBoxLayout()
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("🔎 Search caches...")
        self.search_bar.textChanged.connect(self.filter_cache_tree)
        top_layout.addWidget(self.search_bar)

        refresh_btn = QtWidgets.QPushButton("⟳ Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.populate_cache_tree)
        top_layout.addWidget(refresh_btn)

        main_layout.addLayout(top_layout)

        # --- Cache Tree ---
        self.cache_tree = QtWidgets.QTreeWidget()
        self.cache_tree.setHeaderLabels(["Cache Name", "Date Modified", "Size"])
        self.cache_tree.setColumnWidth(0, 350)
        self.cache_tree.setColumnWidth(1, 180)
        self.cache_tree.setColumnWidth(2, 120)
        self.cache_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.cache_tree.customContextMenuRequested.connect(self.show_cache_context_menu)
        self.cache_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.cache_tree.setSortingEnabled(True)
        main_layout.addWidget(self.cache_tree, 1)

        # --- Bottom Status ---
        bottom_layout = QtWidgets.QVBoxLayout()
        self.status_label = QtWidgets.QLabel("Ready")
        self.disk_summary_label = QtWidgets.QLabel("")
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addWidget(self.disk_summary_label)
        main_layout.addLayout(bottom_layout)

        # --- Load Settings ---
        self.settings = QtCore.QSettings("PLAB", "CacheBrowser")
        saved_path = self.settings.value("cache_dir", "")

        if saved_path and os.path.exists(saved_path):
            self.cache_dir = os.path.normpath(os.path.abspath(saved_path))
        else:
            hip_path = hou.getenv("HIP")
            default1 = os.path.join(hip_path, "Cache")
            default2 = os.path.join(hip_path, "cache")
            if os.path.exists(default1):
                self.cache_dir = os.path.normpath(os.path.abspath(default1))
            elif os.path.exists(default2):
                self.cache_dir = os.path.normpath(os.path.abspath(default2))
            else:
                self.cache_dir = os.path.normpath(os.path.abspath(default1))

        self.path_edit.setText(self.cache_dir)

        # --- Populate Initial Data ---
        self.populate_cache_tree()
        self.center_on_parent()
        self.apply_dark_theme()

    # -------------------------------
    # Cache Population
    # -------------------------------
    def populate_cache_tree(self):
        cache_dir = self.cache_dir
        self.cache_tree.clear()

        if not os.path.exists(cache_dir):
            self.status_label.setText("No Cache directory found.")
            self.disk_summary_label.setText("")
            return

        total_size_bytes = 0

        for cache_name in os.listdir(cache_dir):
            cache_path = os.path.join(cache_dir, cache_name)
            if os.path.isdir(cache_path):
                last_modified = self.get_last_modified_time(cache_path)
                folder_size_bytes = self.get_folder_size_bytes(cache_path)
                total_size_bytes += folder_size_bytes

                parent_item = QtWidgets.QTreeWidgetItem([
                    cache_name,
                    last_modified,
                    self.format_size(folder_size_bytes)
                ])
                self.cache_tree.addTopLevelItem(parent_item)

                # Add version subfolders
                for version in sorted(os.listdir(cache_path)):
                    version_path = os.path.join(cache_path, version)
                    if os.path.isdir(version_path) and version.startswith("v"):
                        version_size_bytes = self.get_folder_size_bytes(version_path)
                        version_item = QtWidgets.QTreeWidgetItem([
                            version,
                            self.get_last_modified_time(version_path),
                            self.format_size(version_size_bytes)
                        ])
                        parent_item.addChild(version_item)

                # Expand only if more than 1 version exists
                parent_item.setExpanded(parent_item.childCount() > 1)

        # Update summary
        self.status_label.setText("Cache list updated.")
        self.update_disk_summary(cache_dir, total_size_bytes)

    def get_last_modified_time(self, path):
        try:
            mtime = os.path.getmtime(path)
            return QtCore.QDateTime.fromSecsSinceEpoch(int(mtime)).toString("yyyy-MM-dd hh:mm")
        except Exception:
            return "Unknown"

    def get_folder_size_bytes(self, path):
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        return total

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def update_disk_summary(self, cache_dir, total_cache_size):
        try:
            usage = shutil.disk_usage(cache_dir)
            free_space = usage.free
            self.disk_summary_label.setText(
                f"📦 Total Cache Size: {self.format_size(total_cache_size)} | 💾 Free Disk Space: {self.format_size(free_space)}"
            )
        except Exception as e:
            self.disk_summary_label.setText(f"Disk usage info unavailable: {e}")

    # -------------------------------
    # Path Setter
    # -------------------------------
    def set_cache_dir(self):
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Cache Directory", self.cache_dir)
        if dir_:
            self.cache_dir = os.path.normpath(os.path.abspath(dir_))
            self.path_edit.setText(self.cache_dir)
            # Save user preference
            self.settings.setValue("cache_dir", self.cache_dir)
            self.populate_cache_tree()

    # -------------------------------
    # Search Filter
    # -------------------------------
    def filter_cache_tree(self, text):
        text = text.lower()
        for i in range(self.cache_tree.topLevelItemCount()):
            parent = self.cache_tree.topLevelItem(i)
            parent_visible = text in parent.text(0).lower()
            child_visible = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                match = text in child.text(0).lower()
                child.setHidden(not match)
                if match:
                    child_visible = True
            parent.setHidden(not (parent_visible or child_visible))

    # -------------------------------
    # Context Menu
    # -------------------------------
    def show_cache_context_menu(self, pos):
        item = self.cache_tree.itemAt(pos)
        if not item:
            return
    
        path = self.get_item_path(item)
    
        menu = QtWidgets.QMenu(self)
    
        # Enable true transparency
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
    
        # Apply flat, rounded, transparent style
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(40, 40, 40, 180);
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
    
        open_action = menu.addAction("📂 Open Folder")
        copy_action = menu.addAction("📋 Copy Path")
        delete_action = menu.addAction("🗑️ Delete Cache")
        override_action = menu.addAction("⬜ Override with Blank")
    
        action = menu.exec_(self.cache_tree.viewport().mapToGlobal(pos))
        if action == open_action:
            self.open_folder(path)
        elif action == copy_action:
            QtWidgets.QApplication.clipboard().setText(path)
            self.status_label.setText("Path copied to clipboard")
        elif action == delete_action:
            self.delete_cache_folder(path)
        elif action == override_action:
            self.override_with_blank(path)

    def get_item_path(self, item):
        parts = []
        while item:
            parts.insert(0, item.text(0).split()[0])
            item = item.parent()
        return os.path.normpath(os.path.abspath(os.path.join(self.cache_dir, *parts)))

    # -------------------------------
    # File Ops
    # -------------------------------
    def open_folder(self, path):
        try:
            if os.path.exists(path):
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"Open folder failed: {e}")

    def delete_cache_folder(self, path):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Cache",
            f"Are you sure you want to delete:\n{path} ?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                shutil.rmtree(path)
                self.populate_cache_tree()
            except Exception as e:
                print(f"Failed to delete cache folder {path}: {e}")

    def override_with_blank(self, path):
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    open(os.path.join(root, f), 'wb').close()
            self.status_label.setText("Cache overridden with blank files.")
        except Exception as e:
            print(f"Failed to override cache: {e}")

    # -------------------------------
    # Double-click opens folder
    # -------------------------------
    def on_item_double_clicked(self, item, column):
        path = self.get_item_path(item)
        self.open_folder(path)

    # -------------------------------
    # Helpers
    # -------------------------------
    def center_on_parent(self):
        if self.parent():
            parent_geom = self.parent().frameGeometry()
            self.move(parent_geom.center() - self.rect().center())
        else:
            screen = QtWidgets.QDesktopWidget().screenGeometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )

    def apply_dark_theme(self):
        modern_stylesheet = """
            QWidget {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border-radius: 4px;
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12px;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #aaaaaa;
                font-size: 12px;
                padding: 0px;
            }
            QLineEdit {
                background-color: #2c2c2c;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 0px 0px;
                color: #fff;
            }
            QLineEdit:focus {
                border: 1px solid #888;
                background-color: #333;
            }
            QTreeWidget {
                background-color: #1e1e1e;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                background-color: transparent;
                margin: 0px 0px;
                padding: 2px;
                border-radius: 0px;
                color: #ddd;
            }
            QTreeWidget::item:selected {
                background-color: #3a6ea5;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background-color: #2d2d2d;
                color: #fff;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #bbbbbb;
                border: none;
                border-bottom: 2px solid #333;
                padding: 2px;
                font-weight: 500;
            }
            QPushButton {
                background-color: #bfbfbf;
                color: #1e1e1e;    
                padding: 2px 2px;
                border-radius: 4px;
                font-weight: 500;
                border: none;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
        """
        self.setStyleSheet(modern_stylesheet)


# -------------------------------
# Launch Helper
# -------------------------------
_cache_browser_instance = None

def show_cache_browser():
    global _cache_browser_instance
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    if _cache_browser_instance is None:
        _cache_browser_instance = CacheBrowser()

        def reset_instance():
            global _cache_browser_instance
            _cache_browser_instance = None

        _cache_browser_instance.destroyed.connect(reset_instance)

    _cache_browser_instance.show()
    _cache_browser_instance.raise_()
    _cache_browser_instance.activateWindow()

    if not QtWidgets.QApplication.instance():
        app.exec_()


# -------------------------------
# Run
# -------------------------------
show_cache_browser()
