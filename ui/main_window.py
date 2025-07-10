import os
import shutil
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSizePolicy,
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QFileIconProvider, QTreeWidget, QTreeWidgetItem, QSizePolicy, QSplitter, QCheckBox, QGroupBox, QRadioButton, QButtonGroup,
    QSpacerItem
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from core.scanner import scan_directory, get_size
from core.utils import format_size
from core.scanner import DirectoryScanner


class MainWindow(QWidget):
    scan_finished = pyqtSignal(dict)
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
        self.progress_layout.addWidget(self.scan_button)  # <-- Ajout du bouton ici

        self.scan_status_label = QLabel("")
        self.progress_layout.addWidget(self.scan_status_label)

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

        # 🥪 Breadcrumb
        self.breadcrumb_layout = QHBoxLayout()
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setLayout(self.breadcrumb_layout)

        self.breadcrumb_spacer = QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.breadcrumb_layout.addItem(self.breadcrumb_spacer)
        self.breadcrumb_widget.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        # Layout central vertical pour breadcrumb + file_list
        self.central_layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.central_layout)

        self.file_list = QTreeWidget()
        self.file_list.setHeaderLabels(["Nom", "Taille"])
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.central_layout.addWidget(self.breadcrumb_widget)  # Breadcrumb en haut
        self.central_layout.addWidget(self.file_list)          # Liste en dessous

        self.main_layout.addWidget(self.sidebar_widget)         # Sidebar à gauche
        self.main_layout.addWidget(self.central_widget)         # Partie centrale à droite

        # 🟦 Arborescence centrale
        # self.tree = QTreeWidget()
        # self.tree.setHeaderLabels(["Nom", "Taille"])
        # self.tree.itemExpanded.connect(self.load_sub_items)
        # self.main_layout.addWidget(self.tree)
        self.scan_finished.connect(self.on_scan_finished)

        self.current_path = None
        # self.breadcrumb_layout = QHBoxLayout()
        # self.breadcrumb_widget = QWidget()
        # self.breadcrumb_widget.setLayout(self.breadcrumb_layout)
        # self.main_layout.addWidget(self.breadcrumb_widget)  # Ajoute la breadcrumb au-dessus de la liste

        # self.file_list = QTreeWidget()
        # self.file_list.setHeaderLabels(["Nom", "Taille"])
        # self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        # self.main_layout.addWidget(self.file_list)


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
        self.file_list.clear()
        # self.progress.setValue(0)
        # self.progress.setVisible(True)
        # self.progress_label.setText("0%")

        self.scan_button.setEnabled(False)
        self.scan_status_label.setText("Scan en cours...")

        # Lance le scan dans un thread séparé
        threading.Thread(target=self.scan_thread, args=(selected_disk,), daemon=True).start()

    def on_scan_finished(self, children_dict):
        self.scanned_data = children_dict
        self.base_disk_path = next(iter(children_dict))  # <-- Ajoute cette ligne
        self.show_folder(self.base_disk_path)
        self.scan_status_label.setText("Scan terminé")
        self.scan_button.setEnabled(True)


    def scan_thread(self, path):
        def update_callback(progress):
            self.progress_changed.emit(progress)

        # Scan complet (lent mais précis)
        data = scan_directory(path, update_callback)
        # On veut un dict: dossier -> liste enfants
        children_dict = {path: data}
        # Pour chaque sous-dossier, ajoute ses enfants récursivement
        for item in data:
            if os.path.isdir(item['path']):
                children_dict.update(self.scan_subfolders(item['path'], update_callback))

        self.scanned_data = children_dict

        # Signale la fin du scan au thread principal (via signal Qt)
        self.scan_finished.emit(children_dict)


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
        if not path or path not in self.scanned_data:
            return

        item.takeChildren()  # nettoie les enfants si déjà chargés

        for child in sorted(self.scanned_data[path], key=lambda x: x['size'], reverse=True):
            size = child['size']
            sub_item = QTreeWidgetItem([child['name'], format_size(size)])
            sub_item.setData(0, Qt.ItemDataRole.UserRole, child['path'])

            if child['is_dir']:
                sub_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

            icon = QIcon("resources/folder.png") if child['is_dir'] else QIcon("resources/file.png")
            sub_item.setIcon(0, icon)

            item.addChild(sub_item)


    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

        # Mise à jour du symbole du bouton
        self.theme_button.setText("🌙" if not self.dark_mode else "☀️")

    def update_progress(self, value):
        self.progress.setValue(value)
        self.progress_label.setText(f"{value}%")

    def update_stats(self):
        path = self.base_disk_path  # Toujours le disque racine
        if os.name == 'nt':
            usage = shutil.disk_usage(path)
            total_disk = usage.total
            used_disk = usage.used
            free_disk = usage.free
        else:
            stat = os.statvfs(path)
            total_disk = stat.f_frsize * stat.f_blocks
            free_disk = stat.f_frsize * stat.f_bfree
            used_disk = total_disk - free_disk

        file_count = self.count_files_recursively(path)

        self.stats_label.setText(
            f"Taille totale : {format_size(total_disk)}\n"
            f"Utilisé : {format_size(used_disk)}\n"
            f"Libre : {format_size(free_disk)}\n"
            f"Fichiers scannés : {file_count}"
        )


    def count_files_recursively(self, path):
        count = 0
        if path not in self.scanned_data:
            return 0

        for item in self.scanned_data[path]:
            if item['is_dir']:
                count += self.count_files_recursively(item['path'])
            else:
                count += 1
        return count



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

                QRadioButton::indicator {
                    width: 10px;
                    height: 10px;
                    border-radius: 5px;
                    border: 2px solid #888;
                    background: #f0f0f0;
                }
                QRadioButton::indicator:checked {
                    background: #4c7bf4;  /* Couleur claire pour la coche */
                    border: 2px solid #fff;
                }
                QRadioButton::indicator:hover {
                    border: 2px solid #4c7bf4;
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

                QRadioButton::indicator {
                    width: 10px;
                    height: 10px;
                    border-radius: 5px;
                    border: 2px solid #888;
                    background: #f0f0f0;
                }
                QRadioButton::indicator:checked {
                    background: #4c7bf4;  /* Couleur claire pour la coche */
                    border: 2px solid #fff;
                }
                QRadioButton::indicator:hover {
                    border: 2px solid #4c7bf4;
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

    def scan_subfolders(self, folder_path, progress_callback):
        """Scan récursivement tous les sous-dossiers et retourne un dict."""
        print(f"[scan_subfolders] Descend dans: {folder_path}")  # <-- Ajout du log
        result = {}
        children = scan_directory(folder_path, progress_callback)
        result[folder_path] = children
        for item in children:
            if os.path.isdir(item['path']):
                result.update(self.scan_subfolders(item['path'], progress_callback))
        print(f"[scan_subfolders] Remontée de: {folder_path}")  # <-- Ajout du log
        return result

    def update_breadcrumb(self, path):
        # Nettoie la barre
        for i in reversed(range(self.breadcrumb_layout.count())):
            item = self.breadcrumb_layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    self.breadcrumb_layout.removeItem(item)
        # Ajoute un bouton pour chaque niveau
        parts = []
        drive, rest = os.path.splitdrive(path)
        if drive:
            parts.append(drive + os.sep)
            rest = rest.lstrip(os.sep)
        if rest:
            parts += rest.split(os.sep)
        current = ""
        for i, part in enumerate(parts):
            if i == 0:
                current = part
            else:
                current = os.path.join(current, part)
            btn = QPushButton(part)
            btn.setFlat(True)
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)  # <-- Compact
            btn.setStyleSheet("padding: 2px 8px; margin: 0 2px;")  # <-- Optionnel, esthétique
            btn.clicked.connect(lambda checked, p=current: self.show_folder(p))
            self.breadcrumb_layout.addWidget(btn)
            if i < len(parts) - 1:
                arrow = QLabel(">")
                arrow.setStyleSheet("padding: 0 4px;")
                self.breadcrumb_layout.addWidget(arrow)
        # Ajoute le spacer à la fin pour pousser les boutons à gauche
        self.breadcrumb_layout.addItem(self.breadcrumb_spacer)

    def show_folder(self, path):
        self.current_path = path
        self.update_breadcrumb(path)
        self.file_list.clear()
        if path not in self.scanned_data:
            return
        for item in sorted(self.scanned_data[path], key=lambda x: x['size'], reverse=True):
            node = QTreeWidgetItem([item['name'], format_size(item['size'])])
            node.setData(0, Qt.ItemDataRole.UserRole, item['path'])
            icon = QIcon("resources/folder.png") if item['is_dir'] else QIcon("resources/file.png")
            node.setIcon(0, icon)
            self.file_list.addTopLevelItem(node)
        self.update_stats()  # <-- Appelle sans argument

    def on_item_double_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        # Si c'est un dossier, on l'affiche
        for child in self.scanned_data.get(self.current_path, []):
            if child['path'] == path and child['is_dir']:
                self.show_folder(path)
                break

    def go_back(self):
        if self.current_path:
            parent = os.path.dirname(self.current_path.rstrip(os.sep))
            if parent and parent in self.scanned_data:
                self.show_folder(parent)

