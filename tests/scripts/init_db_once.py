import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # raiz do projeto
sys.path.append(str(ROOT_DIR))

from src.db.schema import init_db

init_db()
print("DB init OK")
