"""Interface independente do chat; consultas carregadas somente nesta área."""
import pandas as pd
import streamlit as st
from natural_reports import interpret

from reporting import (
    ReportsUnavailable, load_overview, latest_pressure, TOTAL_PARTICIPANTES,
    TOTAL_TRIAGENS, PRESSAO_ACIMA, RISCO, ULTIMA_PRESSAO, STATUS_SM,
    DEMO_TOTAL_PARTICIPANTES, DEMO_TOTAL_TRIAGENS, DEMO_PRESSAO_ACIMA,
    DEMO_RISCO, DEMO_ULTIMA_PRESSAO, DEMO_STATUS_SM, DEMO_ALERT_VALUES,
)


def show_sql(sql):
    with st.expander('Ver SQL'):
        st.code(sql, language='sql')


def readable(frame):
    display = frame.copy()
    for column in display.columns:
        if column == 'data_coleta':
            display[column] = display[column].map(
                lambda value: 'Não informado' if pd.isna(value)
                else pd.Timestamp(value).strftime('%d/%m/%Y %H:%M')
            )
        elif column == 'alerta_critico':
            display[column] = display[column].map(
                lambda value: 'Não informado' if pd.isna(value) else ('Sim' if value is True or value == 1 else 'Não')
            )
        elif column in ('risco', 'status_sindrome_metabolica'):
            display[column] = display[column].fillna('Não informado')
    return display.rename(columns={
        'paciente_id': 'Participante', 'triagem_id': 'Triagem',
        'data_coleta': 'Coleta', 'pas': 'PAS (mmHg)', 'pad': 'PAD (mmHg)',
        'risco': 'Risco registrado', 'alerta_critico': 'Alerta crítico',
        'total_triagens': 'Quantidade de triagens',
        'status_sindrome_metabolica': 'Status registrado de síndrome metabólica',
    })


def render_reports():
    st.title('Relatórios OXICOR')
    st.caption('Consultas somente leitura. Nenhuma classificação clínica é recalculada.')
    st.button('Atualizar relatórios', key='refresh_reports')
    try:
        data = load_overview()
    except ReportsUnavailable as exc:
        st.warning(str(exc))
        return
    if data['source'] == 'demo':
        st.info('**Dados fictícios de demonstração** — origem: CSVs locais de participantes e triagens.')
        queries = {
            'participants': DEMO_TOTAL_PARTICIPANTES,
            'triages': DEMO_TOTAL_TRIAGENS,
            'pressure': DEMO_PRESSAO_ACIMA,
            'risk': DEMO_RISCO,
            'latest': DEMO_ULTIMA_PRESSAO,
            'syndrome': DEMO_STATUS_SM,
            'alerts': DEMO_ALERT_VALUES,
        }
    else:
        st.success('Conexão PostgreSQL confirmada (SELECT 1).')
        queries = {
            'participants': TOTAL_PARTICIPANTES,
            'triages': TOTAL_TRIAGENS,
            'pressure': PRESSAO_ACIMA,
            'risk': RISCO,
            'latest': ULTIMA_PRESSAO,
            'syndrome': STATUS_SM,
            'alerts': 'SELECT alerta_critico, COUNT(*) AS total_triagens FROM triagens GROUP BY alerta_critico ORDER BY alerta_critico;',
        }
    columns = st.columns(4)
    columns[0].metric('Participantes', data['participantes'])
    columns[1].metric('Participantes com PA acima', data['pressao_acima'])
    columns[2].metric('Triagens com alerta crítico', len(data['alertas']) if data['alertas_sql'] else 'Não disponível')
    columns[3].metric('Triagens registradas', data['triagens'])
    st.caption('PA acima: participante com ao menos uma triagem com PAS ≥ 130 ou PAD ≥ 85 mmHg, critério operacional já usado no projeto; não é diagnóstico. Risco, síndrome metabólica e alerta são valores já registrados. Distribuições e alertas contam triagens, não participantes únicos.')
    st.subheader('Pergunte aos dados')
    st.caption('Consultas disponíveis: “Quantos participantes tiveram pressão acima da faixa esperada?” e “Qual foi a última pressão do participante ID?”. Use o ID cadastrado.')
    with st.form('natural_report'):
        question = st.text_input('Sua pergunta sobre os dados', max_chars=250)
        ask = st.form_submit_button('Consultar dados')
    if ask:
        intent, identifier = interpret(question)
        if intent == 'pressure_count':
            st.success(f"{data['pressao_acima']} participante(s) tiveram ao menos uma triagem acima do critério operacional do relatório.")
            show_sql(queries['pressure'])
        elif intent == 'latest_pressure':
            if identifier not in data['pacientes']['paciente_id'].tolist():
                st.info('Participante não encontrado. Confira o ID cadastrado no filtro abaixo.')
            else:
                try:
                    result = latest_pressure(identifier, source=data['source'])
                    if result.empty:
                        st.info('Esse participante não tem triagem registrada.')
                    else:
                        st.dataframe(readable(result), hide_index=True, use_container_width=True)
                    show_sql(queries['latest'])
                except ReportsUnavailable as exc:
                    st.warning(str(exc))
        else:
            st.info('Não reconheci uma das duas consultas disponíveis. Use um dos exemplos acima; nenhuma consulta livre foi executada.')
    if data['triagens'] == 0:
        st.info('Ainda não há triagens registradas. Nenhum dado de demonstração foi criado.')

    st.subheader('1. Total de participantes')
    st.dataframe(pd.DataFrame({'Total de participantes': [data['participantes']]}), hide_index=True)
    show_sql(queries['participants'])

    st.subheader('2. Participantes com pressão acima da faixa esperada')
    st.dataframe(pd.DataFrame({'Participantes distintos': [data['pressao_acima']]}), hide_index=True)
    show_sql(queries['pressure'])

    st.subheader('3. Distribuição por risco')
    st.caption('Contagem de triagens por risco já registrado; não é contagem de participantes únicos.')
    st.dataframe(readable(data['risco']), hide_index=True, use_container_width=True)
    if not data['risco'].empty:
        chart = data['risco'].copy()
        chart['risco'] = chart['risco'].fillna('Não informado')
        st.bar_chart(chart.set_index('risco')['total_triagens'])
    show_sql(queries['risk'])

    st.subheader('4. Última pressão registrada de um paciente')
    with st.form('latest_pressure_filter'):
        paciente_id = st.selectbox('Paciente ID', data['pacientes']['paciente_id'].tolist(), index=None,
                                   placeholder='Selecione um participante existente')
        submitted = st.form_submit_button('Consultar última pressão')
    if submitted and paciente_id is not None:
        try:
            rows = latest_pressure(paciente_id, source=data['source'])
            if rows.empty:
                st.info('Esse participante não tem triagem registrada.')
            else:
                st.dataframe(readable(rows), hide_index=True, use_container_width=True)
        except ReportsUnavailable as exc:
            st.warning(str(exc))
    show_sql(queries['latest'])
    st.caption('O ID selecionado é passado como parâmetro, nunca concatenado ao SQL.')

    st.subheader('5. Triagens com alerta crítico')
    if data['alertas_sql']:
        if data['alertas'].empty:
            st.info('Nenhuma triagem com alerta crítico registrada.')
        st.dataframe(readable(data['alertas']), hide_index=True, use_container_width=True)
        show_sql(data['alertas_sql'])
    else:
        st.warning('O tipo/valores de alerta_critico requerem conferência antes de definir o filtro. Nenhuma equivalência foi presumida.')
        st.dataframe(data['valores_alerta'], hide_index=True)

    st.subheader('6. Síndrome metabólica — status registrados')
    st.caption('Distribuição de triagens pelos valores reais de status_sindrome_metabolica, incluindo os status prováveis/positivos se presentes. Valores são preservados sem inferir equivalências clínicas.')
    st.dataframe(readable(data['sindrome']), hide_index=True, use_container_width=True)
    if not data['sindrome'].empty:
        status = data['sindrome']['status_sindrome_metabolica'].dropna().tolist()
        chosen = st.multiselect('Filtrar status registrados (opcional)', status, key='sm_status')
        if chosen:
            selected = data['sindrome'][data['sindrome']['status_sindrome_metabolica'].isin(chosen)]
            st.metric('Triagens nos status selecionados', int(selected['total_triagens'].sum()))
            st.dataframe(readable(selected), hide_index=True)
    show_sql(queries['syndrome'])

    with st.expander('Conferência dos dados existentes'):
        st.write(f"Participantes: {data['participantes']} · Triagens: {data['triagens']}")
        st.write('Valores reais de alerta_critico:')
        st.dataframe(data['valores_alerta'], hide_index=True)
        st.code(queries['triages'], language='sql')
