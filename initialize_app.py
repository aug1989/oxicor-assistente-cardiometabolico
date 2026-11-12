"""Instala o modelo empacotado somente se o volume ainda não o contiver."""
import shutil
from pathlib import Path
from config import runtime_data_dir
from duckdb_tools import initialize_database

initialize_database()
container_seed = Path(__file__).resolve().parent / 'model_seed'
source = container_seed if container_seed.is_dir() else Path(__file__).resolve().parent / 'data' / 'models' / 'etapa2'
destination = runtime_data_dir() / 'models' / 'etapa2'
if source.exists() and not (destination/'cdc_diabetes_model.pkl').exists():
    destination.mkdir(parents=True,exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path,destination/path.name)
