import os, sys, re, subprocess, datetime
from functools import partial
import hou
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QLabel, QMessageBox, QStyle

XLAB_PATH = os.environ.get("XLAB", "")
HIP_ICON_PATH = os.path.join(XLAB_PATH, "icons", "hipicon.png")

class BrowserTool(QtWidgets.QWidget):
    MAX_RECENT = 10

    def __init__(self, parent=None):
        super(BrowserTool, self).__init__(parent)
        self.settings = QtCore.QSettings("YourStudio", "HoudiniBrowser")
        self.base_sp_path = self.settings.value("browser/base_path", "")
        self.browser_combos = {}

        recent_files = self.settings.value("browser/recent_files", [])
        if isinstance(recent_files, str):
            self.recent_files = [recent_files]
        elif isinstance(recent_files, list):
            self.recent_files = recent_files
        else:
            self.recent_files = []

    def create_browser_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Base Path Row ---
        path_layout = QtWidgets.QHBoxLayout()
        self.base_path_edit = QtWidgets.QLineEdit(self.base_sp_path)
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._browser_browse_base_path)
        path_layout.addWidget(QLabel("Base Path:"))
        path_layout.addWidget(self.base_path_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(0)

        # --- Dropdown Row (Single Line) ---
        labels = ["Project Type", "Project", "Shots", "Sequence", "Shot No", "Task"]
        combos = {}

        combo_layout = QtWidgets.QHBoxLayout()
        combo_layout.setSpacing(2)

        for idx, label in enumerate(labels):
            wrapper = QtWidgets.QVBoxLayout()
            wrapper.setSpacing(2)

            lbl = QtWidgets.QLabel(f"{label}:")
            lbl.setStyleSheet("color: white; font-weight: bold;")

            cb = QtWidgets.QComboBox()
            cb.setEditable(False)
            cb.currentIndexChanged.connect(partial(self._browser_combo_changed, idx))

            if label == "Shot No":
                cb.setMinimumWidth(250)
            else:
                cb.setMinimumWidth(20)

            combos[idx] = cb
            wrapper.addWidget(lbl)
            wrapper.addWidget(cb)
            combo_layout.addLayout(wrapper)

        self.browser_combos = combos
        layout.addLayout(combo_layout)

        # --- Path display and buttons ---
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(2, 2, 2, 2)
        row.setSpacing(2)

        self.browser_path_display = QtWidgets.QLineEdit()
        self.browser_path_display.setPlaceholderText("Type or paste a folder/file path and press Enter")
        self.browser_path_display.returnPressed.connect(self._browser_path_entered)
        row.addWidget(self.browser_path_display)

        back_btn = QtWidgets.QPushButton("Back")
        back_btn.setAutoDefault(False)
        back_btn.setDefault(False)
        back_btn.clicked.connect(self._browser_go_back)
        row.addWidget(back_btn)

        set_btn = QtWidgets.QPushButton("Set")
        set_btn.setAutoDefault(False)
        set_btn.setDefault(False)
        set_btn.clicked.connect(self._browser_save_selection)
        row.addWidget(set_btn)

        open_btn = QtWidgets.QPushButton("Open Folder")
        open_btn.setAutoDefault(False)
        open_btn.setDefault(False)
        open_btn.clicked.connect(self._browser_open_selected)
        row.addWidget(open_btn)

        layout.addLayout(row)

        # --- File list with Recent files below ---
        file_column = QtWidgets.QVBoxLayout()

        # Files (with Date Modified)
        file_column.addWidget(QLabel("Files:"))

        self.browser_file_list = QtWidgets.QTreeWidget()
        self.browser_file_list.setColumnCount(2)
        self.browser_file_list.setHeaderLabels(["Name", "Date Modified"])
        self.browser_file_list.setHeaderHidden(True)   # ✅ hide labels
        self.browser_file_list.setAlternatingRowColors(True)
        self.browser_file_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.browser_file_list.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.browser_file_list.itemDoubleClicked.connect(self._browser_file_double_clicked)
        self.browser_file_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.browser_file_list.customContextMenuRequested.connect(self._show_file_context_menu)
        self.browser_file_list.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.browser_file_list.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        file_column.addWidget(self.browser_file_list, stretch=3)

        # Recent Files
        file_column.addWidget(QLabel("Recent Files:"))
        self.recent_file_list = QtWidgets.QListWidget()
        self.recent_file_list.setAlternatingRowColors(True)
        self.recent_file_list.itemDoubleClicked.connect(self._recent_file_double_clicked)
        file_column.addWidget(self.recent_file_list, stretch=1)

        layout.addLayout(file_column)

        # Populate UI
        self._browser_populate_top()
        self._populate_recent_files()

        # Restore last selected path
        saved = self.settings.value("browser/selected_path", "")
        if saved and os.path.isdir(saved):
            QtCore.QTimer.singleShot(100, lambda p=saved: self._browser_restore_from_path(p))

        return page

    # ---------------- Context menu ----------------
    def _show_file_context_menu(self, position):
        selected_items = self.browser_file_list.selectedItems()
        if not selected_items:
            return

        menu = QtWidgets.QMenu()

        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
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

        open_action = menu.addAction("Open")
        open_ext_action = menu.addAction("Open in External Houdini")
        import_action = menu.addAction("Import")
        import_camera_action = menu.addAction("Import Camera")
        delete_action = menu.addAction("Delete")

        action = menu.exec_(self.browser_file_list.viewport().mapToGlobal(position))
        if not action:
            return

        # Resolve selected paths from UserRole
        paths = []
        for it in selected_items:
            p = it.data(0, QtCore.Qt.UserRole)
            if p and p != "__back__":
                paths.append(p)

        if not paths:
            return

        if action == open_action:
            if len(paths) == 1 and paths[0].lower().endswith(".hip"):
                self._open_hip_file(paths[0])
            else:
                QtWidgets.QMessageBox.information(self, "Open File", "Please select exactly one .hip file to open.")

        elif action == open_ext_action:
            if len(paths) == 1 and paths[0].lower().endswith(".hip"):
                self._open_in_external_houdini(paths[0])
            else:
                QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Select exactly one .hip file to open externally.")

        elif action == import_action:
            self._import_files(paths)

        elif action == import_camera_action:
            abc_files = [f for f in paths if f.lower().endswith(".abc")]
            if abc_files:
                self._import_cameras(abc_files)
            else:
                QtWidgets.QMessageBox.information(self, "Import Camera", "No .abc files selected for importing as camera.")

        elif action == delete_action:
            self._delete_files(paths)

    # ---------------- File open helpers ----------------
    def _open_hip_file(self, path):
        if os.path.isfile(path) and path.lower().endswith(".hip"):
            try:
                hou.hipFile.load(path.replace('\\', '/'))
                self._add_to_recent(path)
            except Exception as e:
                print("Error loading hip file:", e)
                hou.ui.displayMessage(f"Error loading file:\n{e}")
        else:
            QMessageBox.warning(self, "Invalid File", "Only .hip files can be opened.")

    def _open_in_external_houdini(self, path):
        if not os.path.isfile(path) or not path.lower().endswith(".hip"):
            QMessageBox.warning(self, "Invalid File", "Only .hip files can be opened in external Houdini.")
            return

        houdini_versions = []
        hfs_path = os.environ.get("HFS")
        if hfs_path:
            houdini_exec = os.path.join(hfs_path, "bin", "houdini.exe" if sys.platform.startswith("win") else "houdini")
            if os.path.isfile(houdini_exec):
                houdini_versions.append((hfs_path, houdini_exec))

        import glob

        if sys.platform.startswith("win"):
            pattern = r"C:\Program Files\Side Effects Software\Houdini *\bin\houdini.exe"
            for f in glob.glob(pattern):
                if (hfs_path is None) or (os.path.dirname(os.path.dirname(f)) != hfs_path):
                    houdini_versions.append((os.path.dirname(os.path.dirname(f)), f))
        elif sys.platform.startswith("linux"):
            pattern = "/opt/hfs*/bin/houdini"
            for f in glob.glob(pattern):
                if (hfs_path is None) or (os.path.dirname(os.path.dirname(f)) != hfs_path):
                    houdini_versions.append((os.path.dirname(os.path.dirname(f)), f))
        elif sys.platform.startswith("darwin"):
            pattern = "/Applications/Houdini */Houdini.app/Contents/MacOS/houdini"
            for f in glob.glob(pattern):
                if (hfs_path is None) or (os.path.dirname(os.path.dirname(f)) != hfs_path):
                    houdini_versions.append((os.path.dirname(os.path.dirname(f)), f))

        if not houdini_versions:
            QMessageBox.critical(self, "Houdini Not Found", "Could not find any Houdini installations.")
            return

        if len(houdini_versions) == 1:
            exec_path = houdini_versions[0][1]
            try:
                subprocess.Popen([exec_path, path], shell=sys.platform.startswith("win"))
            except Exception as e:
                QMessageBox.critical(self, "Launch Failed", f"Could not launch Houdini:\n{e}")
            return

        items = [os.path.basename(v[0]) for v in houdini_versions]
        item, ok = QtWidgets.QInputDialog.getItem(self, "Select Houdini Version",
                                                  "Choose Houdini version to open:", items, 0, False)
        if ok and item:
            for base, exec_path in houdini_versions:
                if os.path.basename(base) == item:
                    try:
                        subprocess.Popen([exec_path, path], shell=sys.platform.startswith("win"))
                    except Exception as e:
                        QMessageBox.critical(self, "Launch Failed", f"Could not launch Houdini:\n{e}")
                    break

    def _import_files(self, file_list):
        obj = hou.node("/obj")
        for path in file_list:
            if not os.path.isfile(path):
                continue

            filename = os.path.basename(path)
            name_no_ext = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1].lower()
            safe_name = self._sanitize_node_name(name_no_ext)

            try:
                geo_node = obj.createNode("geo", node_name=safe_name, run_init_scripts=False, force_valid_node_name=True)

                if ext == ".abc":
                    alembic_node = geo_node.createNode("alembic", node_name=safe_name)
                    alembic_node.parm("fileName").set(path.replace('\\', '/'))
                else:
                    file_node = geo_node.createNode("file", node_name="file1")
                    file_node.parm("file").set(path.replace('\\', '/'))

                geo_node.layoutChildren()
                self._add_to_recent(path)

            except Exception as e:
                print(f"Import error for {path}:", e)
                hou.ui.displayMessage(f"Failed to import file:\n{path}\n\n{e}")

    def _import_cameras(self, file_list):
        for path in file_list:
            if not os.path.isfile(path) or not path.lower().endswith(".abc"):
                QMessageBox.warning(self, "Invalid File", f"Only .abc files can be imported as cameras:\n{path}")
                continue

            name_no_ext = os.path.splitext(os.path.basename(path))[0]
            safe_name = self._sanitize_node_name(name_no_ext)

            try:
                obj = hou.node("/obj")
                archive_node = obj.createNode(
                    "alembicarchive",
                    node_name=safe_name,
                    run_init_scripts=False,
                    force_valid_node_name=True
                )
                archive_node.parm("fileName").set(path.replace('\\', '/'))
                archive_node.parm("buildHierarchy").pressButton()
                archive_node.layoutChildren()
                self._add_to_recent(path)

            except Exception as e:
                print(f"Import camera error for {path}:", e)
                hou.ui.displayMessage(f"Failed to import camera:\n{path}\n\n{e}")

    def _delete_files(self, file_list):
        confirm = QMessageBox.question(
            self,
            "Delete Files",
            "Are you sure you want to delete these files?\n" + "\n".join(file_list),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            for path in file_list:
                try:
                    os.remove(path)
                except Exception as e:
                    QMessageBox.critical(self, "Delete Failed", f"Could not delete file {path}:\n{e}")
            self._browser_populate_files(self.browser_path_display.text().strip())

    def _save_versioned_hip(self):
        shot = self.browser_combos[4].currentText().strip()
        task = self.browser_combos[5].currentText().strip()
        base_path = self.browser_path_display.text().strip()

        if not shot or not task:
            QMessageBox.warning(self, "Missing Info", "Please select both Shot No and Task.")
            return

        if not os.path.isdir(base_path):
            QMessageBox.warning(self, "Invalid Path", "Target directory is invalid.")
            return

        base_name = f"{shot}_{task}"
        existing = [f for f in os.listdir(base_path) if re.match(rf"{re.escape(base_name)}_v\d{{3}}\.hip", f)]

        version = 1
        if existing:
            versions = [int(re.search(r"_v(\d{3})\.hip", f).group(1)) for f in existing]
            version = max(versions) + 1

        filename = f"{base_name}_v{version:03d}.hip"
        full_path = os.path.join(base_path, filename)

        try:
            hou.hipFile.save(full_path.replace('\\', '/'))
            QMessageBox.information(self, "Saved", f"Scene saved as:\n{filename}")
            self._add_to_recent(full_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def _browser_browse_base_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Base Path", self.base_path_edit.text())
        if folder:
            self.base_path_edit.setText(folder)
            self.base_sp_path = folder
            self.settings.setValue("browser/base_path", folder)
            self.settings.sync()
            self._browser_populate_top()

    def _browser_go_back(self):
        current_path = self.browser_path_display.text().strip()
        if not current_path:
            return
        parent_path = os.path.dirname(current_path)
        if os.path.isdir(parent_path):
            self.browser_path_display.setText(parent_path)
            self._browser_populate_files(parent_path)

    def _browser_populate_top(self):
        base = self.base_path_edit.text().strip()
        try:
            if os.path.isdir(base):
                items = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
                cb = self.browser_combos[0]
                cb.clear()
                cb.addItem("")
                for it in items:
                    cb.addItem(it)
                for i in range(1, 6):
                    self.browser_combos[i].clear()
                self.browser_path_display.setText(base)
        except Exception as e:
            print("Browser top populate error:", e)

    # ---------------- Core: populate QTreeWidget ----------------
    def _browser_populate_files(self, path):
        style = QtWidgets.QApplication.style()
    
        self.browser_file_list.clear()
        try:
            if not os.path.isdir(path):
                return
    
            # Back row
            back_item = QtWidgets.QTreeWidgetItem(["⬅️  Back", ""])
            back_item.setData(0, QtCore.Qt.UserRole, "__back__")
            font = back_item.font(0)
            font.setBold(True)
            back_item.setFont(0, font)
            back_item.setFirstColumnSpanned(True)
            self.browser_file_list.addTopLevelItem(back_item)
    
            entries = sorted(os.listdir(path), key=str.lower)
    
            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
    
            # Add directories with modified date
            for e in dirs:
                full_path = os.path.join(path, e)
                try:
                    mtime = os.path.getmtime(full_path)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = ""
    
                item = QtWidgets.QTreeWidgetItem([e, date_str])
                item.setIcon(0, style.standardIcon(QStyle.SP_DirIcon))
                item.setData(0, QtCore.Qt.UserRole, full_path)
                self.browser_file_list.addTopLevelItem(item)
    
            # Add files with modified date
            for e in files:
                full_path = os.path.join(path, e)
                try:
                    mtime = os.path.getmtime(full_path)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = ""
    
                item = QtWidgets.QTreeWidgetItem([e, date_str])
    
                if e.lower().endswith(".hip") and os.path.exists(HIP_ICON_PATH):
                    item.setIcon(0, QtGui.QIcon(HIP_ICON_PATH))
                else:
                    item.setIcon(0, style.standardIcon(QStyle.SP_FileIcon))
    
                item.setData(0, QtCore.Qt.UserRole, full_path)
                self.browser_file_list.addTopLevelItem(item)
    
        except Exception as e:
            print("browser populate files error:", e)


    def _browser_combo_changed(self, idx, text=None):
        try:
            base_path = self.base_path_edit.text().strip()
            if not base_path or not os.path.isdir(base_path):
                return

            parts = []
            for i in range(0, idx + 1):
                txt = self.browser_combos[i].currentText().strip()
                if txt:
                    parts.append(txt)
                else:
                    break

            path = os.path.join(base_path, *parts) if parts else base_path
            path = os.path.normpath(path)

            next_idx = idx + 1
            if next_idx < len(self.browser_combos):
                cb = self.browser_combos[next_idx]
                cb.clear()
                if os.path.isdir(path):
                    items = sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
                    cb.addItem("")
                    cb.addItems(items)

            deepest_parts = []
            for i in range(len(self.browser_combos)):
                t = self.browser_combos[i].currentText().strip()
                if t:
                    deepest_parts.append(t)
                else:
                    break

            final_path = os.path.join(base_path, *deepest_parts) if deepest_parts else base_path
            final_path = os.path.normpath(final_path)
            self.browser_path_display.setText(final_path)
            self._browser_populate_files(final_path)

        except Exception as e:
            print("browser combo change error:", e)

    def _browser_path_entered(self):
        path = self.browser_path_display.text().strip()
        if os.path.isdir(path):
            self._browser_populate_files(path)
        elif os.path.isfile(path):
            # Open the file directly based on extension
            ext = os.path.splitext(path)[1].lower()
            if ext == ".hip":
                self._open_hip_file(path)
            elif ext == ".abc":
                self._import_files([path])
            else:
                self._import_files([path])
            # Also refresh the containing folder in the tree
            folder = os.path.dirname(path)
            if os.path.isdir(folder):
                self.browser_path_display.setText(folder)
                self._browser_populate_files(folder)
        else:
            QMessageBox.warning(self, "Invalid Path", "The entered path does not exist.")

    def _browser_save_selection(self):
        path = self.browser_path_display.text().strip()
        if not path:
            return
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Invalid Path", "Selected path does not exist.")
            return
        self.settings.setValue("browser/selected_path", path)
        self.settings.sync()
        QMessageBox.information(self, "Saved", f"Path saved:\n{path}")

    def _browser_open_selected(self):
        path = self.browser_path_display.text().strip()
        if path and os.path.isdir(path):
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, "Not Found", "Selected path not found.")

    def _browser_restore_from_path(self, fullpath):
        try:
            fullpath = os.path.normpath(fullpath)
            base = os.path.normpath(self.base_sp_path)
            if not fullpath.startswith(base):
                return
            rel = os.path.relpath(fullpath, base)
            parts = rel.split(os.sep)
            for i, p in enumerate(parts):
                if i > 5:
                    break
                cb = self.browser_combos[i]
                if cb.count() == 0 and i == 0:
                    self._browser_populate_top()
                idx = cb.findText(p)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self.browser_path_display.setText(fullpath)
            self._browser_populate_files(fullpath)
        except Exception as e:
            print("browser restore error:", e)

    def _sanitize_node_name(self, name):
        name = re.sub(r'\W', '_', name)
        if not re.match(r'^[A-Za-z_]', name):
            name = '_' + name
        return name

    def _browser_file_double_clicked(self, item, column):
        # QTreeWidgetItem: data is stored in column 0
        if item.data(0, QtCore.Qt.UserRole) == "__back__":
            self._browser_go_back()
            return

        path = item.data(0, QtCore.Qt.UserRole)
        if not path:
            return

        if os.path.isdir(path):
            self.browser_path_display.setText(path)
            self._browser_populate_files(path)
            return

        ext = os.path.splitext(path)[1].lower()
        name_no_ext = os.path.splitext(os.path.basename(path))[0]
        safe_name = self._sanitize_node_name(name_no_ext)

        try:
            if ext == ".hip":
                hou.hipFile.load(path.replace('\\', '/'))
            elif ext == ".abc":
                obj = hou.node("/obj")
                geo_node = obj.createNode("geo", node_name=safe_name,
                                          run_init_scripts=False, force_valid_node_name=True)
                alembic_node = geo_node.createNode("alembic", node_name=safe_name)
                alembic_node.parm("fileName").set(path.replace('\\', '/'))
                geo_node.layoutChildren()
            else:
                obj = hou.node("/obj")
                geo_node = obj.createNode("geo", node_name=safe_name,
                                          run_init_scripts=False, force_valid_node_name=True)
                file_node = geo_node.createNode("file", node_name="file1")
                file_node.parm("file").set(path.replace('\\', '/'))
                geo_node.layoutChildren()

            self._add_to_recent(path)

        except Exception as e:
            print(f"Error opening file: {e}")
            try:
                hou.ui.displayMessage(f"Error opening file:\n{e}")
            except:
                pass

    # ---------------- Recent ----------------
    def _add_to_recent(self, filepath):
        filepath = os.path.normpath(filepath)
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        if len(self.recent_files) > self.MAX_RECENT:
            self.recent_files = self.recent_files[:self.MAX_RECENT]
        self.settings.setValue("browser/recent_files", self.recent_files)
        self.settings.sync()
        self._populate_recent_files()

    def _populate_recent_files(self):
        self.recent_file_list.clear()
        for f in self.recent_files:
            if os.path.exists(f) and f.lower().endswith(".hip"):
                self.recent_file_list.addItem(f)

    def _recent_file_double_clicked(self, item):
        full_path = item.text()
        if os.path.exists(full_path):
            ext = os.path.splitext(full_path)[1].lower()
            name_no_ext = os.path.splitext(os.path.basename(full_path))[0]
            safe_name = self._sanitize_node_name(name_no_ext)
            try:
                if ext == ".hip":
                    hou.hipFile.load(full_path.replace('\\', '/'))
                elif ext == ".abc":
                    obj = hou.node("/obj")
                    geo_node = obj.createNode("geo", node_name=safe_name, run_init_scripts=False, force_valid_node_name=True)
                    alembic_node = geo_node.createNode("alembic", node_name=safe_name)
                    alembic_node.parm("fileName").set(full_path.replace('\\', '/'))
                    geo_node.layoutChildren()
                else:
                    obj = hou.node("/obj")
                    geo_node = obj.createNode("geo", node_name=safe_name, run_init_scripts=False, force_valid_node_name=True)
                    file_node = geo_node.createNode("file", node_name="file1")
                    file_node.parm("file").set(full_path.replace('\\', '/'))
                    geo_node.layoutChildren()

                self.browser_path_display.setText(os.path.dirname(full_path))
                self._browser_populate_files(os.path.dirname(full_path))
                self._add_to_recent(full_path)

            except Exception as e:
                print(f"Error opening recent file: {e}")
                try:
                    hou.ui.displayMessage(f"Error opening file:\n{e}")
                except:
                    pass
        else:
            QMessageBox.warning(self, "File Not Found", "The recent file no longer exists.")
            if full_path in self.recent_files:
                self.recent_files.remove(full_path)
                self.settings.setValue("browser/recent_files", self.recent_files)
                self.settings.sync()
            self._populate_recent_files()

def show_browser_tool():
    try:
        if hasattr(hou.session, "browser_tool_ui"):
            old_win = hou.session.browser_tool_ui
            if old_win is not None:
                if old_win.isVisible():
                    old_win.raise_()
                    old_win.activateWindow()
                    return
                else:
                    hou.session.browser_tool_ui = None

        main_window = hou.ui.mainQtWindow()
        tool = BrowserTool()

        DARK_STYLE = """
        QWidget {
            background-color: #1e1e1e;
            color: #FFFFFF;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            font-size: 12px;
        }
        QLineEdit, QComboBox, QListWidget, QTreeWidget {
            background-color: #2c2c2c;
            border: none;
            border-radius: 4px;
            outline: none;
        }
        QLineEdit:focus, QComboBox:focus, QListWidget:focus, QTreeWidget:focus {
            border: 1px solid #00aaff;
        }
        QPushButton {
            background-color: #bfbfbf;
            color: #1e1e1e;
            padding: 1px 1px;
            border-radius: 4px;
            font-weight: 400;
            min-width: 40px;
        }
        QPushButton:hover { background-color: #555555; }
        QPushButton:pressed { background-color: #222222; }
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #005f87;
            color: #ffffff;
        }
        QScrollBar:vertical {
            background: #2b2b2b;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover { background: #888888; }
        """

        win = QtWidgets.QMainWindow(parent=main_window)
        win.setWindowTitle("Houdini Browser Tool")
        win.setMinimumSize(900, 550)
        win.setStyleSheet(DARK_STYLE)
        win.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint |
            QtCore.Qt.WindowCloseButtonHint
        )

        central_widget = QtWidgets.QWidget()
        stacked_layout = QtWidgets.QStackedLayout()
        central_widget.setLayout(stacked_layout)
        win.setCentralWidget(central_widget)

        main_page = tool.create_browser_page()
        stacked_layout.addWidget(main_page)

        save_btn = QtWidgets.QPushButton("💾 ")
        save_btn.setParent(central_widget)
        save_btn.setToolTip("Save Hip File")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1e1e1e;
                font-weight: bold;
                border-radius: 10px;
                padding: 0px;
                border: 0px solid rgba(255, 255, 255, 0);
            }
            QPushButton:hover { background-color: rgba(76, 175, 80, 0.0); color: rgba(76, 175, 80, 0.9);}
        """)
        save_btn.resize(40, 40)
        save_btn.clicked.connect(tool._save_versioned_hip)

        def reposition_button():
            parent_size = central_widget.size()
            btn_width, btn_height = save_btn.size().width(), save_btn.size().height()
            save_btn.move(parent_size.width() - btn_width - 20, parent_size.height() - btn_height - 20)

        central_widget.resizeEvent = lambda event: reposition_button()

        win.show()
        hou.session.browser_tool_ui = win

    except Exception as e:
        print("Failed to open browser tool:", e)

# Run it
show_browser_tool()
