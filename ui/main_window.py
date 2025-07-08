import os
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox,
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QFileIconProvider, QTreeWidget, QTreeWidgetItem, QLineEdit, QSplitter
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from core.scanner import scan_directory
from core.utils import format_size

class MainWindow(QWidget):
    scan_finished = pyqtSignal(str, list)  # path, data

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DiskSpace Analyzer")
        self.resize(1000, 700)

        self.scan_finished.connect(self.build_tree)

        self.layout = QVBoxLayout(self)

        # Disque à scanner
        self.disk_selector = QComboBox()
        self.populate_disks()
        self.layout.addWidget(QLabel("Sélectionner un disque :"))
        self.layout.addWidget(self.disk_selector)

        # Bouton de scan
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.layout.addWidget(self.scan_button)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.layout.addWidget(self.progress)

        # Split entre arbre et fichiers
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Taille"])
        self.tree.itemExpanded.connect(self.load_sub_items)

        self.splitter.addWidget(self.tree)
        self.layout.addWidget(self.splitter)

        # Données du scan
        self.current_path = None
        self.scanned_data = {}

    def populate_disks(self):
        # Windows only for now (optionnel : cross-platform plus tard)
        if os.name == 'nt':
            import string
            from ctypes import windll
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            self.disk_selector.addItems(drives)
        else:
            self.disk_selector.addItem("/")  # Linux/macOS

    def start_scan(self):
        selected_drive = self.disk_selector.currentText()
        if not selected_drive:
            return

        self.tree.clear()
        self.scanned_data = {}
        self.progress.setValue(0)

        self.current_path = selected_drive

        thread = threading.Thread(target=self.scan_thread, args=(selected_drive,))
        thread.start()

    def scan_thread(self, path):
        def update_callback(progress):
            self.progress.setValue(progress)

        data = scan_directory(path, update_callback)
        self.scanned_data[path] = data

        # Signale la fin du scan au thread principal
        self.scan_finished.emit(path, data)


    def build_tree(self, base_path, data):
        self.tree.clear()
        for item in sorted(data, key=lambda x: x['size'], reverse=True):
            node = QTreeWidgetItem([item['name'], format_size(item['size'])])
            node.setData(0, Qt.ItemDataRole.UserRole, item['path'])

            icon = QIcon("resources/folder.png") if os.path.isdir(item['path']) else QIcon("resources/file.png")
            node.setIcon(0, icon)

            if os.path.isdir(item['path']):
                node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

            self.tree.addTopLevelItem(node)



    def load_sub_items(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isdir(path):
            return

        children = scan_directory(path)
        for child in sorted(children, key=lambda x: x['size'], reverse=True):
            sub_item = QTreeWidgetItem([child['name'], format_size(child['size'])])
            sub_item.setData(0, Qt.ItemDataRole.UserRole, child['path'])
            if os.path.isdir(child['path']):
                sub_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            item.addChild(sub_item)
