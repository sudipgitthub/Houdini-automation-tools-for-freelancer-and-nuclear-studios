import hou
from PySide2 import QtWidgets, QtCore, QtGui


# Function to recursively find all camera nodes
def find_all_cameras(node):
    cameras = []
    if node.type().name() == "cam":
        cameras.append(node)

    for child in node.children():
        cameras.extend(find_all_cameras(child))

    return cameras


# Custom QListWidgetItem to allow coloring active camera
class CameraListItem(QtWidgets.QListWidgetItem):
    def __init__(self, cam_node):
        super(CameraListItem, self).__init__(cam_node.path())
        self.cam_node = cam_node
        self.update_tooltip()

    def update_tooltip(self):
        try:
            resx = self.cam_node.parm("resx").eval()
            resy = self.cam_node.parm("resy").eval()
            focal = self.cam_node.parm("focal").eval()
            near = self.cam_node.parm("near").eval()
            far = self.cam_node.parm("far").eval()
            tooltip = f"""
            📷 Camera: {self.cam_node.name()}
            Path: {self.cam_node.path()}
            Resolution: {int(resx)} x {int(resy)}
            Focal Length: {focal:.2f}
            Clipping: {near:.2f} - {far:.2f}
            """
            self.setToolTip(tooltip)
        except:
            self.setToolTip(self.cam_node.path())


# Main UI Class
class CameraFinderUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(CameraFinderUI, self).__init__(parent)

        self.setWindowTitle("🎥 Houdini Camera Finder")
        self.resize(900, 550)  # allow resizable instead of fixed size

        # ✅ Enable Minimize / Maximize / Close buttons
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint |
            QtCore.Qt.WindowCloseButtonHint
        )

        # QMainWindow needs a central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        # Apply modern dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #dddddd;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #bfbfbf;
                color: #1e1e1e;
                padding: 1px 1px;
                border-radius: 4px;
                font-weight: 400;
                transition: background-color 0.2s ease, color 0.2s ease;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 2px;
            }
            QListWidget::item {
                border-radius: 4px;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #007acc;
                color: white;
            }
        """)

        # Main layout inside central widget
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 🔽 Everything else in your UI stays exactly the same 🔽
        # Top button bar
        button_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(button_layout)

        self.find_button = QtWidgets.QPushButton("🔍 Find All Cameras")
        self.find_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        button_layout.addWidget(self.find_button)

        self.refresh_button = QtWidgets.QPushButton("🔄 Refresh")
        self.refresh_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch(1)

        # Camera list
        self.camera_list = QtWidgets.QListWidget()
        self.camera_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.camera_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.camera_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.camera_list)

        # Connect signals
        self.find_button.clicked.connect(self.populate_camera_list)
        self.refresh_button.clicked.connect(self.populate_camera_list)
        self.camera_list.itemDoubleClicked.connect(self._look_through_camera)

        # Setup hotkeys
        self._setup_shortcuts()

        # Populate on startup
        self.populate_camera_list()

    # ----------------------------
    # HOTKEYS
    # ----------------------------
    def _setup_shortcuts(self):
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Return"), self,
                            activated=lambda: self._look_through_selected())
        QtWidgets.QShortcut(QtGui.QKeySequence("Del"), self,
                            activated=self._delete_selected_cameras)
        QtWidgets.QShortcut(QtGui.QKeySequence("PageDown"), self,
                            activated=self._next_camera)
        QtWidgets.QShortcut(QtGui.QKeySequence("PageUp"), self,
                            activated=self._prev_camera)

    def _look_through_selected(self):
        selected = self.camera_list.selectedItems()
        if selected:
            self._look_through_camera(selected[0])

    def _next_camera(self):
        row = self.camera_list.currentRow()
        if row < self.camera_list.count() - 1:
            self.camera_list.setCurrentRow(row + 1)
            self._look_through_selected()

    def _prev_camera(self):
        row = self.camera_list.currentRow()
        if row > 0:
            self.camera_list.setCurrentRow(row - 1)
            self._look_through_selected()

    # ----------------------------
    # CORE FUNCTIONS
    # ----------------------------
    def populate_camera_list(self):
        self.camera_list.clear()

        root = hou.node("/obj")
        if not root:
            QtWidgets.QMessageBox.warning(self, "Error", "Root /obj node not found.")
            return

        cameras = find_all_cameras(root)

        if not cameras:
            self.camera_list.addItem("No cameras found.")
            return

        # find active camera
        active_cam = None
        scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if scene_viewer:
            viewport = scene_viewer.curViewport()
            active_cam = viewport.camera()

        for cam in cameras:
            item = CameraListItem(cam)
            if active_cam and cam == active_cam:
                item.setForeground(QtGui.QBrush(QtGui.QColor("lime")))  # highlight active cam
                item.setText(f"⭐ {cam.path()}")
            self.camera_list.addItem(item)

    def _show_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        selected_items = self.camera_list.selectedItems()
        if selected_items:
            menu.addAction("📋 Copy Path(s)", self._copy_selected_paths)
            menu.addAction("👁 Look Through Camera", lambda: self._look_through_camera(selected_items[0]))
            menu.addAction("🗑 Delete Camera(s)", self._delete_selected_cameras)
            menu.addAction("📍 Select in Network Editor", self._select_in_network)
            menu.addAction("🎯 Set Camera Parm on Selected Node(s)", lambda: self._set_camera_parm(selected_items[0]))

        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(40, 40, 40, 220);
                border: 1px solid rgba(90, 90, 90, 150);
                border-radius: 6px;
                padding: 2px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 2px 20px;
                border-radius: 6px;
                color: #dddddd;
            }
            QMenu::item:selected {
                background-color: rgba(0, 122, 204, 150);
                color: white;
            }
        """)
        menu.exec_(self.camera_list.viewport().mapToGlobal(pos))

    def _copy_selected_paths(self):
        paths = [item.text().replace("⭐ ", "") for item in self.camera_list.selectedItems()]
        QtWidgets.QApplication.clipboard().setText("\n".join(paths))

    def _look_through_camera(self, item):
        cam_path = item.text().replace("⭐ ", "")
        cam_node = hou.node(cam_path)
        if not cam_node:
            return
        try:
            scene_viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            if scene_viewer:
                viewport = scene_viewer.curViewport()
                viewport.setCamera(cam_node)
                self.populate_camera_list()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to set viewport camera:\n{e}")

    def _delete_selected_cameras(self):
        for item in self.camera_list.selectedItems():
            cam_path = item.text().replace("⭐ ", "")
            cam_node = hou.node(cam_path)
            if not cam_node:
                continue

            parent = cam_node.parent()
            if parent and parent.path() != "/obj":
                # ✅ Delete parent subnet if not in /obj
                parent.destroy()
            else:
                # ✅ Delete only camera if directly under /obj
                if cam_node.type().name() == "cam":
                    cam_node.destroy()

        self.populate_camera_list()


    def _select_in_network(self):
        nodes = [hou.node(item.text().replace("⭐ ", "")) for item in self.camera_list.selectedItems()]
        nodes = [n for n in nodes if n]
        if nodes:
            hou.clearAllSelected()
            for n in nodes:
                n.setSelected(True, clear_all_selected=False)
            pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if pane:
                pane.homeToSelection()

    def _set_camera_parm(self, item):
        cam_path = item.text().replace("⭐ ", "")
        cam_node = hou.node(cam_path)
        if not cam_node:
            return

        selected_nodes = hou.selectedNodes()
        if not selected_nodes:
            QtWidgets.QMessageBox.information(self, "No Node Selected",
                                              "Please select one or more nodes in the Network Editor.")
            return

        success = False
        for node in selected_nodes:
            parm = node.parm("camera")
            if parm:
                parm.set(cam_node.path())
                success = True

        if success:
            QtWidgets.QMessageBox.information(self, "Success",
                                              f"Camera set to {cam_node.path()} on selected node(s).")
        else:
            QtWidgets.QMessageBox.warning(self, "No Camera Parm Found",
                                          "None of the selected nodes have a 'camera' parameter.")


# --------------------------
# Global instance + launcher
# --------------------------
_camera_finder_instance = None

def show_camera_finder():
    global _camera_finder_instance

    # If already open → just focus it
    if _camera_finder_instance is not None:
        try:
            _camera_finder_instance.raise_()
            _camera_finder_instance.activateWindow()
            return
        except RuntimeError:
            # Old reference is dead → reset
            _camera_finder_instance = None

    # Otherwise create new
    _camera_finder_instance = CameraFinderUI(hou.ui.mainQtWindow())
    _camera_finder_instance.show()

    
show_camera_finder()    