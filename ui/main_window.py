from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
import threading
from scanner import get_folder_size
from utils.size_formatter import format_size

class DiskAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Explorateur d'espace disque")
        self.setGeometry(100, 100, 400, 200)

        self.layout = QVBoxLayout()
        self.label = QLabel("Sélectionne un dossier à analyser")
        self.layout.addWidget(self.label)

        self.button = QPushButton("Choisir un dossier")
        self.button.clicked.connect(self.choose_folder)
        self.layout.addWidget(self.button)

        self.result_label = QLabel("")
        self.layout.addWidget(self.result_label)

        self.setLayout(self.layout)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.result_label.setText("Analyse en cours...")
            threading.Thread(target=self.analyze_folder, args=(folder,)).start()

    def analyze_folder(self, folder):
        size = get_folder_size(folder)
        self.result_label.setText(f"Taille du dossier : {format_size(size)}")
