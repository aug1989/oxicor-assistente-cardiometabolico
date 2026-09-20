"""Consultas fixas de leitura: PostgreSQL -> cursor -> pandas.

Nenhuma query fornecida pelo usuário é executada. O filtro é parametrizado.
Não há conexão com o SQLite usado para o histórico do chat neste módulo.
"""
import os
from contextlib import contextmanager

import pandas as pd
import psycopg


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


@contextmanager
def connection():
    required = ('POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD')
    if any(not os.environ.get(key) for key in required):
        raise ReportsUnavailable('Conexão ainda não configurada. Preencha as variáveis POSTGRES_ no .env e recrie somente o Streamlit.')
    try:
        port = int(os.environ.get('POSTGRES_PORT', '5432'))
        with psycopg.connect(
            host=os.environ['POSTGRES_HOST'], port=port,
            dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'],
            password=os.environ['POSTGRES_PASSWORD'], connect_timeout=5,
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
        return pd.DataFrame(cursor.fetchall(), columns=[col.name for col in cursor.description])


def load_overview():
    with connection() as conn:
        check = dataframe(conn, 'SELECT 1 AS conexao_ok;')
        result = {
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


def latest_pressure(paciente_id):
    with connection() as conn:
        return dataframe(conn, ULTIMA_PRESSAO, {'paciente_id': paciente_id})
