#!/usr/bin/env python3
"""
Script pour corriger les problèmes de compatibilité dans swaggerpy pour Python 3.12
"""

import os
import sys
import re
from pathlib import Path

def find_swaggerpy_path():
    """Trouve le chemin d'installation de swaggerpy"""
    import site
    for path in site.getsitepackages():
        swaggerpy_path = Path(path) / "swaggerpy"
        if swaggerpy_path.exists():
            return swaggerpy_path
    return None

def fix_init_imports(swaggerpy_path):
    """Corrige les imports dans __init__.py"""
    init_file = swaggerpy_path / "__init__.py"
    if not init_file.exists():
        print(f"Fichier {init_file} non trouvé")
        return False
    
    # Sauvegarde du fichier original
    backup_file = swaggerpy_path / "__init__.py.backup"
    if not backup_file.exists():
        with open(init_file, 'r') as f:
            content = f.read()
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"Sauvegarde créée: {backup_file}")
    
    # Correction des imports
    with open(init_file, 'r') as f:
        content = f.read()
    
    content = content.replace("from swagger_model import", "from .swagger_model import")
    content = content.replace("from processors import", "from .processors import")
    
    with open(init_file, 'w') as f:
        f.write(content)
    
    print(f"Imports corrigés dans {init_file}")
    return True

def fix_urlparse_import(swaggerpy_path):
    """Corrige l'import urlparse dans swagger_model.py"""
    model_file = swaggerpy_path / "swagger_model.py"
    if not model_file.exists():
        print(f"Fichier {model_file} non trouvé")
        return False
    
    # Sauvegarde du fichier original
    backup_file = swaggerpy_path / "swagger_model.py.backup"
    if not backup_file.exists():
        with open(model_file, 'r') as f:
            content = f.read()
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"Sauvegarde créée: {backup_file}")
    
    # Correction de l'import urlparse
    with open(model_file, 'r') as f:
        content = f.read()
    
    if "import urlparse" in content:
        content = content.replace(
            "import urlparse", 
            "try:\n    import urlparse\nexcept ImportError:\n    from urllib import parse as urlparse"
        )
        
        with open(model_file, 'w') as f:
            f.write(content)
        
        print(f"Import urlparse corrigé dans {model_file}")
        return True
    else:
        print("Import urlparse non trouvé ou déjà corrigé")
        return False

def main():
    """Fonction principale"""
    print("Recherche de l'installation de swaggerpy...")
    swaggerpy_path = find_swaggerpy_path()
    
    if not swaggerpy_path:
        print("swaggerpy non trouvé. Veuillez spécifier le chemin manuellement.")
        if len(sys.argv) > 1:
            swaggerpy_path = Path(sys.argv[1])
        else:
            sys.exit(1)
    
    print(f"swaggerpy trouvé à: {swaggerpy_path}")
    
    # Correction des imports dans __init__.py
    fix_init_imports(swaggerpy_path)
    
    # Correction de l'import urlparse dans swagger_model.py
    fix_urlparse_import(swaggerpy_path)
    
    print("\nCorrections terminées. Veuillez redémarrer votre application.")

if __name__ == "__main__":
    main()
