"""Consultas fixas somente leitura em PostgreSQL ou DuckDB de demonstração.

Nenhuma query fornecida pelo usuário é executada. O filtro é parametrizado.
Não há conexão com o SQLite usado para o histórico do chat neste módulo.
"""
from contextlib import contextmanager

import pandas as pd
import psycopg

from config import get_setting

class ReportsUnavailable(Exception):
    """Mensagem pública sem credenciais, DSN ou detalhes do servidor."""


TOTAL_PARTICIPANTES = 'SELECT COUNT(*) AS total_participantes FROM participantes;'
TOTAL_TRIAGENS = 'SELECT COUNT(*) AS total_triagens FROM triagens;'
PRESSAO_ACIMA = '''SELECT COUNT(DISTINCT paciente_id) AS participantes_pressao_acima
FROM triagens
WHERE pas >= 130 OR pad >= 85;'''
RISCO = '''SELECT risco, COUNT(*) AS total_triagens
FROM triagens
GROUP BY risco
ORDER BY total_triagens DESC, risco;'''
ULTIMA_PRESSAO = '''SELECT paciente_id, data_coleta, pas, pad, triagem_id
FROM triagens
WHERE paciente_id = %(paciente_id)s
ORDER BY data_coleta DESC, triagem_id DESC
LIMIT 1;'''
STATUS_SM = '''SELECT status_sindrome_metabolica, COUNT(*) AS total_triagens
FROM triagens
GROUP BY status_sindrome_metabolica
ORDER BY total_triagens DESC, status_sindrome_metabolica;'''
ALERT_VALUES = '''SELECT alerta_critico, COUNT(*) AS total_triagens
FROM triagens GROUP BY alerta_critico ORDER BY alerta_critico;'''
ALERT_TYPE = '''SELECT data_type FROM information_schema.columns
WHERE table_schema = current_schema() AND table_name = 'triagens'
AND column_name = 'alerta_critico';'''
PATIENT_IDS = 'SELECT paciente_id FROM participantes ORDER BY paciente_id;'

DEMO_TOTAL_PARTICIPANTES = 'SELECT COUNT(*) AS total_participantes FROM participantes;'
DEMO_TOTAL_TRIAGENS = 'SELECT COUNT(*) AS total_triagens FROM triagens;'
DEMO_PRESSAO_ACIMA = '''SELECT COUNT(DISTINCT paciente_id) AS participantes_pressao_acima
FROM triagens
WHERE pas >= 130 OR pad >= 85;'''
DEMO_RISCO = '''SELECT risco, COUNT(*) AS total_triagens
FROM triagens
GROUP BY risco
ORDER BY total_triagens DESC, risco;'''
DEMO_ULTIMA_PRESSAO = '''SELECT paciente_id, data_coleta, pas, pad, triagem_id
FROM triagens
WHERE paciente_id = ?
ORDER BY data_coleta DESC, triagem_id DESC
LIMIT 1;'''
DEMO_STATUS_SM = '''SELECT status_sindrome_metabolica, COUNT(*) AS total_triagens
FROM triagens
GROUP BY status_sindrome_metabolica
ORDER BY total_triagens DESC, status_sindrome_metabolica;'''
DEMO_ALERT_VALUES = '''SELECT alerta_critico, COUNT(*) AS total_triagens
FROM triagens
GROUP BY alerta_critico
ORDER BY alerta_critico;'''
DEMO_ALERTS = '''SELECT triagem_id, paciente_id, data_coleta, pas, pad, risco, alerta_critico
FROM triagens
WHERE alerta_critico IS TRUE
ORDER BY data_coleta DESC, triagem_id DESC;'''


def postgres_configuration():
    required = ('POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD')
    return {key: get_setting(key) for key in required}


def postgres_is_configured(settings=None):
    settings = settings or postgres_configuration()
    return all(settings.values())


@contextmanager
def connection():
    settings = postgres_configuration()
    if not postgres_is_configured(settings):
        raise ReportsUnavailable('Configure todos os secrets/variáveis POSTGRES_ para usar PostgreSQL.')
    try:
        port = int(get_setting('POSTGRES_PORT', '5432'))
        with psycopg.connect(
            host=settings['POSTGRES_HOST'], port=port,
            dbname=settings['POSTGRES_DB'], user=settings['POSTGRES_USER'],
            password=settings['POSTGRES_PASSWORD'], connect_timeout=5,
            application_name='oxicor_streamlit_relatorios',
            options='-c default_transaction_read_only=on -c statement_timeout=10000',
        ) as conn:
            # Snapshot consistente entre contagens, categorias e tabelas.
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            yield conn
    except (psycopg.Error, ValueError):
        raise ReportsUnavailable('Não foi possível consultar o PostgreSQL. Confira as credenciais, acesso de rede e as tabelas participantes/triagens; detalhes da conexão não são exibidos.') from None


def dataframe(conn, sql, params=None):
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [
            column.name if hasattr(column, 'name') else column[0]
            for column in cursor.description
        ]
        return pd.DataFrame(cursor.fetchall(), columns=columns)


def load_overview():
    settings = postgres_configuration()
    configured = [bool(value) for value in settings.values()]
    if not any(configured):
        return load_demo_overview()
    if not all(configured):
        raise ReportsUnavailable(
            'Configuração PostgreSQL incompleta. Preencha todos os secrets POSTGRES_ ou remova-os para usar os dados fictícios locais.'
        )

    with connection() as conn:
        check = dataframe(conn, 'SELECT 1 AS conexao_ok;')
        result = {
            'source': 'postgresql',
            'conexao_ok': int(check.iloc[0, 0]) == 1,
            'participantes': int(dataframe(conn, TOTAL_PARTICIPANTES).iloc[0, 0]),
            'triagens': int(dataframe(conn, TOTAL_TRIAGENS).iloc[0, 0]),
            'pressao_acima': int(dataframe(conn, PRESSAO_ACIMA).iloc[0, 0]),
            'risco': dataframe(conn, RISCO),
            'sindrome': dataframe(conn, STATUS_SM),
            'valores_alerta': dataframe(conn, ALERT_VALUES),
            'pacientes': dataframe(conn, PATIENT_IDS),
        }
        # Primeiro inspecionar o tipo real; nunca converter texto desconhecido em boolean.
        types = dataframe(conn, ALERT_TYPE)
        dtype = types.iloc[0, 0] if not types.empty else None
        values = [value for value in result['valores_alerta']['alerta_critico'] if value is not None]
        if dtype == 'boolean':
            predicate = 'alerta_critico IS TRUE'
        elif dtype in ('smallint', 'integer', 'bigint') and all(value in (0, 1) for value in values):
            predicate = 'alerta_critico = 1'
        else:
            predicate = None
        result['alerta_tipo'] = dtype
        result['alertas_sql'] = None
        result['alertas'] = pd.DataFrame()
        if predicate:
            sql = ('SELECT triagem_id, paciente_id, data_coleta, pas, pad, risco, alerta_critico\n'
                   f'FROM triagens WHERE {predicate}\nORDER BY data_coleta DESC, triagem_id DESC;')
            result['alertas_sql'] = sql
            result['alertas'] = dataframe(conn, sql)
        return result


def load_demo_overview():
    import duckdb

    from duckdb_tools import DB_PATH, initialize_database

    initialize_database()
    if not DB_PATH.is_file():
        raise ReportsUnavailable('A base DuckDB de demonstração não foi inicializada.')
    try:
        with duckdb.connect(
            str(DB_PATH),
            read_only=True,
            config={'enable_external_access': False},
        ) as conn:
            participants = dataframe(conn, DEMO_TOTAL_PARTICIPANTES)
            triages = dataframe(conn, DEMO_TOTAL_TRIAGENS)
            pressure = dataframe(conn, DEMO_PRESSAO_ACIMA)
            risk = dataframe(conn, DEMO_RISCO)
            syndrome = dataframe(conn, DEMO_STATUS_SM)
            alert_values = dataframe(conn, DEMO_ALERT_VALUES)
            alerts = dataframe(conn, DEMO_ALERTS)
            patients = dataframe(conn, PATIENT_IDS)
    except duckdb.Error:
        raise ReportsUnavailable(
            'Não foi possível consultar a base DuckDB local. Confira os CSVs fictícios de participantes e triagens.'
        ) from None

    return {
        'source': 'demo',
        'conexao_ok': True,
        'participantes': int(participants.iloc[0, 0]),
        'triagens': int(triages.iloc[0, 0]),
        'pressao_acima': int(pressure.iloc[0, 0]),
        'risco': risk,
        'sindrome': syndrome,
        'valores_alerta': alert_values,
        'alertas_sql': DEMO_ALERTS,
        'alertas': alerts,
        'alerta_tipo': 'BOOLEAN',
        'pacientes': patients,
    }


def latest_pressure(paciente_id, source='postgresql'):
    if source == 'demo':
        import duckdb

        from duckdb_tools import DB_PATH

        try:
            with duckdb.connect(
                str(DB_PATH),
                read_only=True,
                config={'enable_external_access': False},
            ) as conn:
                return dataframe(conn, DEMO_ULTIMA_PRESSAO, [paciente_id])
        except duckdb.Error:
            raise ReportsUnavailable(
                'Não foi possível consultar a última pressão na base de demonstração.'
            ) from None
    with connection() as conn:
        return dataframe(conn, ULTIMA_PRESSAO, {'paciente_id': paciente_id})
