import os
import shutil
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSizePolicy,
    QPushButton, QProgressBar, QListWidget, QListWidgetItem,
    QFileIconProvider, QTreeWidget, QTreeWidgetItem, QSizePolicy, QSplitter, QCheckBox, QGroupBox, QRadioButton, QButtonGroup,
    QSpacerItem, QFileDialog
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

        self.folder_button = QPushButton("Sélectionner un dossier...")
        self.folder_button.clicked.connect(self.select_folder)
        self.sidebar_layout.addWidget(self.folder_button)

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

        # === 3️⃣ Statistiques du scan
        self.stats_group = QGroupBox("Statistiques du scan")
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
        self.scan_type = None  # "disk" ou "folder"
        # self.breadcrumb_layout = QHBoxLayout()
        # self.breadcrumb_widget = QWidget()
        # self.breadcrumb_widget.setLayout(self.breadcrumb_layout)
        # self.main_layout.addWidget(self.breadcrumb_widget)  # Ajoute la breadcrumb au-dessus de la liste

        # self.file_list = QTreeWidget()
        # self.file_list.setHeaderLabels(["Nom", "Taille"])
        # self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        # self.main_layout.addWidget(self.file_list)

        self.scan_running = False  # ← Ajoute cette ligne


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

        # Retire la sélection automatique du premier disque
        # if self.disk_radiobuttons:
        #     self.disk_radiobuttons[0].setChecked(True)

        for radio in self.disk_radiobuttons:
            radio.toggled.connect(self.on_disk_selected)

    def on_disk_selected(self, checked):
        if checked:
            self.selected_path = self.disk_buttongroup.checkedButton().text()
            self.selected_type = "disk"
            self.scan_status_label.setText(f"Disque sélectionné : {self.selected_path}")
        else:
            # Ne rien faire si un dossier est sélectionné
            if self.selected_type == "folder":
                return
            # Si aucun disque n'est sélectionné, on efface le chemin
            if not any(radio.isChecked() for radio in self.disk_radiobuttons):
                self.selected_path = None
                self.selected_type = None

    def start_scan(self):
        if self.scan_running:
            self.scan_status_label.setText("Un scan est déjà en cours.")
            return
        if not self.selected_path or not self.selected_type:
            self.scan_status_label.setText("Veuillez sélectionner un disque ou un dossier avant de lancer le scan.")
            return

        self.file_list.clear()
        self.file_list.setDisabled(True)
        self.breadcrumb_widget.setDisabled(True)  # Désactive le fil d'ariane
        self.scan_button.setEnabled(False)
        self.folder_button.setEnabled(False)
        self.scan_running = True
        if self.selected_type == "disk":
            self.scan_status_label.setText(f"Scan du disque {self.selected_path} en cours...")
        else:
            self.scan_status_label.setText(f"Scan du dossier {self.selected_path} en cours...")
        self.scan_type = self.selected_type
        threading.Thread(target=self.scan_thread, args=(self.selected_path,), daemon=True).start()

    def on_scan_finished(self, children_dict):
        self.scanned_data = children_dict
        self.base_disk_path = next(iter(children_dict))
        self.show_folder(self.base_disk_path)
        self.scan_status_label.setText("Scan terminé")
        self.scan_button.setEnabled(True)
        self.folder_button.setEnabled(True)
        self.file_list.setDisabled(False)
        self.breadcrumb_widget.setDisabled(False)  # Réactive le fil d'ariane
        self.scan_running = False


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
        path = self.base_disk_path
        file_count = self.count_files_recursively(path)
        if self.scan_type == "disk":
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

            self.stats_label.setText(
                f"Type : Disque\n"
                f"Taille totale : {format_size(total_disk)}\n"
                f"Utilisé : {format_size(used_disk)}\n"
                f"Libre : {format_size(free_disk)}\n"
                f"Fichiers scannés : {file_count}"
            )
        else:
            folder_size = get_size(path)
            self.stats_label.setText(
                f"Type : Dossier\n"
                f"Taille totale : {format_size(folder_size)}\n"
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
        # Couleurs et styles identiques pour les deux thèmes
        base_bg = "#1e1e1e" if self.dark_mode else "#ffffff"
        text_color = "white" if self.dark_mode else "black"
        group_bg = base_bg
        border_color = "#888" if self.dark_mode else "#ddd"
        button_bg = "#2d2d2d" if self.dark_mode else "#f0f0f0"
        button_hover = "#3c3c3c" if self.dark_mode else "#e2e2e2"
        button_text = text_color
        progress_bg = "#2c2c2c" if self.dark_mode else "#eee"
        progress_chunk = "#a45de4" if self.dark_mode else "#4c7bf4"
        header_bg = "#2a2a2a" if self.dark_mode else "#f5f5f5"
        header_text = text_color
        scrollbar_bg = "#2c2c2c" if self.dark_mode else "#f0f0f0"
        scrollbar_handle = "#555" if self.dark_mode else "#ccc"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {base_bg};
                color: {text_color};
            }}

            QGroupBox {{
                border: 1px solid {border_color};
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
                background-color: {group_bg};
            }}

            QGroupBox::title {{
                subcontrol-origin: content;
                subcontrol-position: top left;
                padding: 0px 6px 2px 6px;
                color: {text_color};
                font-weight: 600;
            }}

            QLabel, QRadioButton {{
                color: {text_color};
            }}

            QRadioButton::indicator {{
                width: 10px;
                height: 10px;
                border-radius: 5px;
                border: 2px solid #888;
                background: #f0f0f0;
            }}
            QRadioButton::indicator:checked {{
                background: #4c7bf4;
                border: 2px solid #fff;
            }}
            QRadioButton::indicator:hover {{
                border: 2px solid #4c7bf4;
            }}

            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }}

            QPushButton:hover {{
                background-color: {button_hover};
            }}

            QProgressBar {{
                border: 1px solid #444;
                border-radius: 4px;
                background-color: {progress_bg};
            }}

            QProgressBar::chunk {{
                background-color: {progress_chunk};
                border-radius: 4px;
            }}

            QTreeWidget {{
                background-color: {base_bg};
                color: {text_color};
                border: none;
            }}

            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_text};
                border: none;
                padding: 6px;
            }}

            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {scrollbar_bg};
                width: 10px;
                height: 10px;
            }}

            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {scrollbar_handle};
                border-radius: 5px;
            }}
        """)

    def scan_subfolders(self, folder_path, progress_callback):
        """Scan récursivement tous les sous-dossiers et retourne un dict."""# <-- Ajout du log
        result = {}
        children = scan_directory(folder_path, progress_callback)
        result[folder_path] = children
        for item in children:
            if os.path.isdir(item['path']):
                result.update(self.scan_subfolders(item['path'], progress_callback))
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

        parts = []
        # Si scan d'un dossier, on part du dossier sélectionné
        if self.scan_type == "folder":
            # On veut le chemin relatif à la racine scannée
            base = self.base_disk_path
            rel_path = os.path.relpath(path, base)
            # Si on est sur la racine, juste le nom du dossier
            if rel_path == ".":
                parts = [os.path.basename(base)]
            else:
                parts = [os.path.basename(base)] + rel_path.split(os.sep)
            current = base
            for i, part in enumerate(parts):
                if i == 0:
                    current = base
                else:
                    current = os.path.join(current, part)
                btn = QPushButton(part)
                btn.setFlat(True)
                btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                btn.setStyleSheet("padding: 2px 8px; margin: 0 2px;")
                btn.clicked.connect(lambda checked, p=current: self.show_folder(p))
                self.breadcrumb_layout.addWidget(btn)
                if i < len(parts) - 1:
                    arrow = QLabel(">")
                    arrow.setStyleSheet("padding: 0 4px;")
                    self.breadcrumb_layout.addWidget(arrow)
        else:
            # Comportement disque comme avant
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
                btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                btn.setStyleSheet("padding: 2px 8px; margin: 0 2px;")
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

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier à scanner")
        if folder:
            self.selected_path = folder
            self.selected_type = "folder"
            # Tronque le chemin si trop long
            display_path = folder
            max_len = 40
            if len(folder) > max_len:
                display_path = "..." + folder[-(max_len-3):]
            self.scan_status_label.setText(f"Dossier sélectionné : {display_path}")
            self.disk_buttongroup.setExclusive(False)
            for radio in self.disk_radiobuttons:
                radio.setChecked(False)
            self.disk_buttongroup.setExclusive(True)

