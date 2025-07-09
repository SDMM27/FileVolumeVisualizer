import os
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox,
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QFileIconProvider, QTreeWidget, QTreeWidgetItem, QSizePolicy, QSplitter, QCheckBox, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from core.scanner import scan_directory
from core.utils import format_size

class MainWindow(QWidget):
    scan_finished = pyqtSignal(str, list)
    progress_changed = pyqtSignal(int)

    def __init__(self):

        super().__init__()
        self.dark_mode = True  # ⬅️ change ça pour tester
        self.apply_theme()
        self.setWindowTitle("DiskSpace Analyzer")
        self.resize(1200, 700)

        # Layout principal horizontal
        self.main_layout = QHBoxLayout(self)
        self.setLayout(self.main_layout)

        # 🟩 Layout intérieur pour les cards (sidebar)
        self.sidebar_layout = QVBoxLayout()
        self.theme_button = QPushButton("🌙")  # ou "☀️" selon ton style
        self.theme_button.setFixedSize(30, 30)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.sidebar_layout.addWidget(self.theme_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.sidebar_layout.setSpacing(8)
        self.sidebar_layout.setContentsMargins(8, 8, 8, 8)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === 1️⃣ Sélection du disque
        self.disk_group = QGroupBox("Sélection du disque")
        self.disk_layout = QVBoxLayout()
        self.disk_layout.setContentsMargins(6, 18, 6, 6)  # ← top augmenté
        self.disk_radiobuttons = []
        self.disk_buttongroup = QButtonGroup(self)
        self.disk_buttongroup.setExclusive(True)
        self.populate_disks()
        self.disk_group.setLayout(self.disk_layout)
        self.disk_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.sidebar_layout.addWidget(self.disk_group)

        # === 2️⃣ Progression & Scan
        self.progress_group = QGroupBox("Progression du scan")
        self.progress_layout = QVBoxLayout()
        self.progress_layout.setContentsMargins(8, 18, 8, 8)
        self.progress_layout.setSpacing(4)

        self.scan_button = QPushButton("Démarrer le scan")
        self.scan_button.clicked.connect(self.start_scan)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress_changed.connect(self.progress.setValue)

        self.progress_bar_layout = QHBoxLayout()
        self.progress_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("color: white;")  # ou noir en mode clair

        self.progress_bar_layout.addWidget(self.progress)
        self.progress_bar_layout.addWidget(self.progress_label)

        self.progress_changed.connect(self.update_progress)

        self.progress_layout.addWidget(self.scan_button)
        self.progress_layout.addSpacing(8)  # <-- Espace entre bouton et barre
        self.progress_layout.addLayout(self.progress_bar_layout)
        self.progress_group.setLayout(self.progress_layout)
        self.progress_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.sidebar_layout.addWidget(self.progress_group)

        # === 3️⃣ Statistiques disque
        self.stats_group = QGroupBox("Statistiques du disque")
        self.stats_layout = QVBoxLayout()
        self.stats_layout.setContentsMargins(6, 18, 6, 6)

        self.stats_label = QLabel("Taille totale :\nUtilisé :\nLibre :\nFichiers scannés :")
        self.stats_layout.addWidget(self.stats_label)

        self.stats_group.setLayout(self.stats_layout)
        self.stats_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.sidebar_layout.addWidget(self.stats_group)

        # === 4️⃣ Filtres
        self.filters_group = QGroupBox("Filtres")
        self.filters_layout = QVBoxLayout()
        self.filters_layout.setContentsMargins(6, 18, 6, 6)

        self.filters_label = QLabel("🔧 Filtres à venir...")
        self.filters_layout.addWidget(self.filters_label)

        self.filters_group.setLayout(self.filters_layout)
        self.filters_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.sidebar_layout.addWidget(self.filters_group)

        # 📦 Conteneur de la sidebar (cartes alignées en haut uniquement)
        self.sidebar_container = QWidget()
        self.sidebar_container.setLayout(self.sidebar_layout)

        # 📐 Layout enveloppant pour caler en haut + garder largeur fixe
        self.sidebar_wrapper_layout = QVBoxLayout()
        self.sidebar_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_wrapper_layout.setSpacing(0)
        self.sidebar_wrapper_layout.addWidget(self.sidebar_container)
        self.sidebar_wrapper_layout.addStretch(1)  # Pushes cards en haut

        self.sidebar_widget = QWidget()
        self.sidebar_widget.setLayout(self.sidebar_wrapper_layout)
        self.sidebar_widget.setFixedWidth(280)

        self.main_layout.addWidget(self.sidebar_widget)

        # 🟦 Arborescence centrale
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nom", "Taille"])
        self.tree.itemExpanded.connect(self.load_sub_items)
        self.main_layout.addWidget(self.tree)

    def populate_disks(self):
        self.disk_radiobuttons.clear()

        if os.name == 'nt':
            import string
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            index = 0
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    path = f"{letter}:\\"
                    radio = QRadioButton(path)
                    self.disk_radiobuttons.append(radio)
                    self.disk_buttongroup.addButton(radio, index)
                    self.disk_layout.addWidget(radio)
                    index += 1
                bitmask >>= 1
        else:
            radio = QRadioButton("/")
            self.disk_radiobuttons.append(radio)
            self.disk_buttongroup.addButton(radio, 0)
            self.disk_layout.addWidget(radio)

        # Sélectionne le premier disque par défaut
        if self.disk_radiobuttons:
            self.disk_radiobuttons[0].setChecked(True)


    def start_scan(self):
        selected_button = self.disk_buttongroup.checkedButton()
        if not selected_button:
            return

        selected_disk = selected_button.text()
        self.tree.clear()
        self.scanned_data = {}
        self.progress.setValue(0)

        self.progress.setVisible(True)

        thread = threading.Thread(target=self.scan_thread, args=(selected_disk,))
        thread.start()



    def scan_thread(self, path):
        def update_callback(progress):
            self.progress_changed.emit(progress)


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

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

        # Mise à jour du symbole du bouton
        self.theme_button.setText("🌙" if not self.dark_mode else "☀️")

    def update_progress(self, value):
        self.progress.setValue(value)
        self.progress_label.setText(f"{value}%")


    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: white;
                }

                QGroupBox {
                    border: 1px solid #888;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding: 10px;
                    background-color: #1e1e1e;
                }

                QGroupBox::title {
                    subcontrol-origin: content;
                    subcontrol-position: top left;
                    padding: 0px 6px 2px 6px;
                    color: white;
                    font-weight: 600;
                }

                QLabel, QRadioButton {
                    color: white;
                }

                QPushButton {
                    background-color: #2d2d2d;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 5px;
                }

                QPushButton:hover {
                    background-color: #3c3c3c;
                }

                QProgressBar {
                    border: 1px solid #444;
                    border-radius: 4px;
                    background-color: #2c2c2c;
                }

                QProgressBar::chunk {
                    background-color: #a45de4;
                    border-radius: 4px;
                }

                QTreeWidget {
                    background-color: #1e1e1e;
                    color: white;
                    border: none;
                }

                QHeaderView::section {
                    background-color: #2a2a2a;
                    color: white;
                    border: none;
                    padding: 6px;
                }

                QScrollBar:vertical, QScrollBar:horizontal {
                    background: #2c2c2c;
                    width: 10px;
                    height: 10px;
                }

                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background: #555;
                    border-radius: 5px;
                }
            """)

        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: white;
                    color: black;
                }

                QGroupBox {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 10px;
                    background-color: white;
                }

                QGroupBox::title {
                    subcontrol-origin: content;
                    subcontrol-position: top left;
                    padding: 0px 6px 2px 6px;
                    color: #222;
                    font-weight: 600;
                }

                QLabel, QRadioButton {
                    color: #222;
                }

                QPushButton {
                    background-color: #f0f0f0;
                    color: black;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px;
                }

                QPushButton:hover {
                    background-color: #e2e2e2;
                }

                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #eee;
                }

                QProgressBar::chunk {
                    background-color: #4c7bf4;
                    border-radius: 4px;
                }

                QTreeWidget {
                    background-color: white;
                    color: black;
                    border: none;
                }

                QHeaderView::section {
                    background-color: #f5f5f5;
                    color: black;
                    border: none;
                    padding: 6px;
                }

                QScrollBar:vertical, QScrollBar:horizontal {
                    background: #f0f0f0;
                    width: 10px;
                    height: 10px;
                }

                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background: #ccc;
                    border-radius: 5px;
                }
            """)

