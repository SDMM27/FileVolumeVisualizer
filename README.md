# FileVolumeVisualizer

**FileVolumeVisualizer** est une application graphique pour explorer l’occupation de l’espace disque ou d’un dossier, visualiser l’arborescence, et filtrer les fichiers/dossiers par taille.

## Fonctionnalités

- Scan d’un disque ou d’un dossier
- Affichage arborescent des fichiers et dossiers
- Filtre par taille minimale (Mo)
- Statistiques détaillées (taille totale, utilisée, libre, nombre de fichiers)
- Thème clair/sombre

## Installation

### Version exécutable (Windows)

1. Téléchargez le fichier `FileVolumeVisualizer.exe` depuis la [release GitHub](https://github.com/SDMM27/FileVolumeVisualizer/releases).
2. Exécutez le fichier téléchargé.

### Version Python

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/SDMM27/FileVolumeVisualizer.git
   cd FileVolumeVisualizer
   pip install -r requirements.txt
   python main.py
   ```

## Utilisation

- Sélectionnez un disque ou un dossier à scanner.
- Cliquez sur “Démarrer le scan”.
- Naviguez dans l’arborescence.
- Utilisez le filtre pour n’afficher que les éléments dépassant une certaine taille.