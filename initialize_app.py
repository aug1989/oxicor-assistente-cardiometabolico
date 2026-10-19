"""Instala o modelo empacotado somente se o volume ainda não o contiver."""
import shutil
from pathlib import Path
from duckdb_tools import initialize_database

initialize_database()
source = Path('/app/model_seed')
destination = Path('/app/data/models/etapa2')
if source.exists() and not (destination/'cdc_diabetes_model.pkl').exists():
    destination.mkdir(parents=True,exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path,destination/path.name)
