"""Consultas analíticas fixas; o agente nunca recebe SQL ou caminhos do usuário."""
import json
import os
import unicodedata
from pathlib import Path

DB_PATH = Path(os.getenv('OXICOR_DUCKDB_PATH', '/app/data/oxicor.duckdb'))

def normalized(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()

def initialize_database(seed_dir='/app/seed'):
    import duckdb
    if DB_PATH.exists():
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DB_PATH.with_suffix('.building.duckdb')
    with duckdb.connect(str(temporary)) as conn:
        for table, name in [('participantes', 'participantes.csv'), ('triagens', 'triagens.csv'), ('cdc', 'cdc_diabetes_health_indicators.csv')]:
            path = Path(seed_dir) / name
            conn.execute(f'CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?)', [str(path)])
    temporary.replace(DB_PATH)

def query_data(question):
    import duckdb
    text = normalized(question)
    if not DB_PATH.exists():
        return 'Base DuckDB indisponível. A inicialização do aplicativo precisa importar os CSVs.'
    if any(word in text for word in ('cdc', 'dataset', 'base publica')):
        sql = 'SELECT COUNT(*) AS registros, AVG(BMI) AS imc_medio, SUM(CASE WHEN Diabetes_binary=1 THEN 1 ELSE 0 END) AS classe_positiva FROM cdc'
        source = 'Dataset público CDC usado no projeto; estatísticas da amostra, não da população.'
    elif any(word in text for word in ('pressao', 'hipertens')):
        sql = 'SELECT COUNT(DISTINCT paciente_id) AS participantes_pressao_acima FROM triagens WHERE pas >= 130 OR pad >= 85'
        source = 'CSV local de triagens. Filtro operacional existente: PAS >= 130 ou PAD >= 85; não é diagnóstico.'
    elif 'risco' in text:
        sql = 'SELECT risco, COUNT(*) AS total_triagens FROM triagens GROUP BY risco ORDER BY risco'
        source = 'CSV local de triagens; categorias já registradas.'
    elif 'triagen' in text or 'triagem' in text:
        sql = 'SELECT COUNT(*) AS total_triagens FROM triagens'
        source = 'CSV local de triagens.'
    elif 'participante' in text:
        sql = 'SELECT COUNT(*) AS total_participantes FROM participantes'
        source = 'CSV local de participantes.'
    else:
        return 'Consultas permitidas: total de participantes, total de triagens, contagem por risco, pressão acima do filtro ou resumo do dataset CDC. Não executo SQL fornecido na pergunta.'
    with duckdb.connect(str(DB_PATH), read_only=True, config={'enable_external_access': False}) as conn:
        cursor = conn.execute(sql)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return json.dumps({'fonte': source, 'resultado': rows}, ensure_ascii=False, default=str)

if __name__ == '__main__':
    initialize_database()
