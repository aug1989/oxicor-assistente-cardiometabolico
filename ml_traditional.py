from __future__ import annotations

import json
import pickle
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
MODEL_DIR = DATA_DIR / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)
METADATA_PATH = DATA_DIR / 'cdc_diabetes_metadata.json'
DEFAULT_MODEL_PATHS = [
    MODEL_DIR / 'etapa2' / 'cdc_diabetes_model.pkl',
    MODEL_DIR / 'cdc_diabetes_model.pkl',
    Path.home() / 'Downloads' / 'cdc_diabetes_model.pkl',
    Path.home() / 'Downloads' / 'cdc_diabetes_model',
]
DATASET_CANDIDATES = [
    'https://archive.ics.uci.edu/static/public/891/cdc+diabetes+health+indicators.zip',
    'https://archive.ics.uci.edu/static/public/891/data.csv',
]

DEFAULT_TARGET = 'Diabetes_binary'
AVAILABLE_ESTIMATORS = ['xgboost', 'lgbm', 'rf', 'extra_tree']


def _default_columns() -> dict[str, str]:
    return {
        'Diabetes_binary': 'Alvo binário: 0 = sem diabetes, 1 = diabetes ou pré-diabetes.',
        'HighBP': 'Hipertensão arterial.',
        'HighChol': 'Colesterol alto.',
        'CholCheck': 'Verificação recente do colesterol.',
        'BMI': 'Índice de massa corporal.',
        'Smoker': 'Tabagismo atual.',
        'Stroke': 'Histórico de acidente vascular cerebral.',
        'HeartDiseaseorAttack': 'Doença cardíaca ou infarto.',
        'PhysActivity': 'Atividade física recente.',
        'Fruits': 'Consumo de frutas.',
        'Veggies': 'Consumo de vegetais.',
        'HvyAlcoholConsump': 'Consumo pesado de álcool.',
        'AnyHealthcare': 'Acesso a cuidados de saúde.',
        'NoDocbcCost': 'Barreira por custo para atendimento.',
        'GenHlth': 'Autoavaliação geral da saúde.',
        'MentHlth': 'Dias de má saúde mental nos últimos 30 dias.',
        'PhysHlth': 'Dias de má saúde física nos últimos 30 dias.',
        'DiffWalk': 'Dificuldade para caminhar ou subir escadas.',
        'Sex': 'Sexo do participante.',
        'Age': 'Faixa etária.',
        'Education': 'Nível educacional.',
        'Income': 'Faixa de renda.',
    }


def _save_metadata(payload: dict | None = None) -> dict:
    data = payload or {
        'dataset_name': 'CDC Diabetes Health Indicators',
        'source_url': 'https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators',
        'target_column': DEFAULT_TARGET,
        'drop_suggestions': ['Diabetes_binary', 'Education', 'Income', 'ID'],
        'columns': _default_columns(),
    }
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def load_metadata() -> dict:
    if METADATA_PATH.exists():
        try:
            return json.loads(METADATA_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    return _save_metadata()


COLUMN_DESCRIPTIONS = load_metadata().get('columns', _default_columns())


def suggest_columns_to_remove() -> list[str]:
    metadata = load_metadata()
    suggestions = metadata.get('drop_suggestions', [])
    return [column for column in suggestions if isinstance(column, str)]


def normalize_drop_columns(
    dataset_columns: Sequence[str],
    target_col: str,
    selected_drop: Sequence[str] | None = None,
) -> list[str]:
    defaults = suggest_columns_to_remove()
    chosen = list(selected_drop) if selected_drop is not None else defaults
    normalized = []
    seen = set()
    for column in chosen + [target_col]:
        if column not in dataset_columns:
            continue
        if column in seen:
            continue
        normalized.append(column)
        seen.add(column)
    return normalized


def prepare_feature_frame(
    df: pd.DataFrame,
    target_col: str = DEFAULT_TARGET,
    drop_candidates: Sequence[str] | None = None,
) -> pd.DataFrame:
    frame = df.copy()
    if target_col in frame.columns:
        frame = frame.drop(columns=[target_col])
    selected = list(drop_candidates) if drop_candidates is not None else suggest_columns_to_remove()
    for column in selected:
        if column in frame.columns:
            frame = frame.drop(columns=[column])
    return frame


def resolve_model_path(model_path: str | Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if model_path is not None:
        path = Path(model_path)
        candidates.extend([
            path,
            path.with_suffix('.pkl'),
            Path(str(path) + '.pkl'),
        ])
    candidates.extend(DEFAULT_MODEL_PATHS)
    for candidate in candidates:
        candidate = candidate.expanduser().resolve() if candidate.exists() else candidate.expanduser()
        if candidate.exists():
            return candidate
    return None


def _bool_from_text(text: str) -> int | None:
    normalized = text.lower().strip()
    if normalized in {'1', 'sim', 's', 'yes', 'true', 'ativo'}:
        return 1
    if normalized in {'0', 'nao', 'não', 'n', 'no', 'false', 'inativo', 'sem'}:
        return 0
    return None


def parse_prediction_payload(question: str, candidate_columns: Sequence[str] | None = None) -> dict[str, Any]:
    text = (question or '')
    normalized = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').lower()
    columns = list(candidate_columns) if candidate_columns else list(COLUMN_DESCRIPTIONS.keys())
    payload: dict[str, Any] = {}

    mapping = {
        'HighBP': ['pressao alta', 'hipertensao', 'hipertensão', 'highbp'],
        'HighChol': ['colesterol alto', 'highchol', 'colesterol elevado'],
        'CholCheck': ['checagem colesterol', 'checagem de colesterol', 'cholcheck', 'colesterol verificado'],
        'BMI': ['bmi', 'imc', 'indice de massa corporal'],
        'Smoker': ['fumante', 'smoker', 'tabagismo'],
        'Stroke': ['avc', 'stroke'],
        'HeartDiseaseorAttack': ['doenca cardiaca', 'infarto', 'heartdiseaseorattack'],
        'PhysActivity': ['atividade fisica', 'atividade física', 'physactivity'],
        'Fruits': ['frutas', 'fruits'],
        'Veggies': ['vegetais', 'veggies'],
        'HvyAlcoholConsump': ['alcool pesado', 'álcool pesado', 'hvyalcoholconsump'],
        'AnyHealthcare': ['seguro de saude', 'anyhealthcare', 'atendimento'],
        'NoDocbcCost': ['custo consulta', 'custo de consulta', 'nodocbccost', 'nao foi ao medico por custo'],
        'GenHlth': ['saude geral', 'genhlth', 'estado geral de saude'],
        'MentHlth': ['dias de saude mental', 'menthlth', 'saude mental'],
        'PhysHlth': ['dias de saude fisica', 'physhlth', 'saude fisica'],
        'DiffWalk': ['dificuldade para caminhar', 'diffwalk', 'andar'],
        'Sex': ['sexo', 'sex'],
        'Age': ['idade', 'age'],
        'Education': ['educacao', 'educação', 'education'],
        'Income': ['renda', 'income'],
    }

    for column in columns:
        synonyms = mapping.get(column, [column.lower()])
        for synonym in synonyms:
            explicit_negation = re.search(rf'(?:sem|nao|nao tem|não|nunca|ausente)\s+{re.escape(synonym)}', normalized)
            for match in re.finditer(rf'{re.escape(synonym)}\s*(?:[:=]|\b(?:e|eh|de|igual|é)\b\s*)?(\d+(?:[.,]\d+)?)', normalized):
                value = match.group(1).replace(',', '.')
                payload[column] = float(value) if '.' in value else int(float(value))
                break
            if column in payload:
                break
            for match in re.finditer(rf'{re.escape(synonym)}\s*(?:[:=]|\b(?:e|eh|de|igual|é)\b\s*)?(sim|nao|não|yes|no|1|0)', normalized):
                value = _bool_from_text(match.group(1))
                if value is not None:
                    payload[column] = value
                    break
            if column in payload:
                break
            if column == 'Age' and re.search(rf'\b(\d{{1,3}})\s*(?:anos|ano)\b', normalized):
                age_match = re.search(rf'\b(\d{{1,3}})\s*(?:anos|ano)\b', normalized)
                if age_match:
                    payload[column] = int(age_match.group(1))
            if column == 'BMI' and re.search(rf'\bimc\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\b', normalized):
                bmi_match = re.search(rf'\bimc\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\b', normalized)
                if bmi_match:
                    payload[column] = float(bmi_match.group(1).replace(',', '.'))
            if column in payload:
                break
            if synonym in normalized and not explicit_negation:
                if column in {'HighBP', 'HighChol', 'CholCheck', 'Smoker', 'Stroke', 'HeartDiseaseorAttack', 'PhysActivity', 'AnyHealthcare', 'DiffWalk', 'HvyAlcoholConsump', 'Fruits', 'Veggies', 'NoDocbcCost'}:
                    payload[column] = 1
                    break
    if 'Age' in payload and isinstance(payload['Age'], float) and payload['Age'].is_integer():
        payload['Age'] = int(payload['Age'])
    return payload


def _download_dataset_csv(save_path: Path) -> pd.DataFrame:
    import requests
    import zipfile
    import io

    save_path.parent.mkdir(parents=True, exist_ok=True)
    for url in DATASET_CANDIDATES:
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            if url.endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    csv_file = next(
                        (name for name in archive.namelist() if name.lower().endswith('.csv') and 'diabetes' in name.lower()),
                        None,
                    )
                    if csv_file is None:
                        continue
                    df = pd.read_csv(archive.open(csv_file))
                    save_path.write_bytes(response.content)
                    df.to_csv(save_path.with_suffix('.csv'), index=False)
                    return df
            if url.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(response.content))
                df.to_csv(save_path, index=False)
                return df
        except Exception:
            continue
    raise RuntimeError('Não foi possível baixar o dataset do UCI para a pasta de dados.')


@st.cache_data(show_spinner=False)
def load_cdc_dataset(force_reload: bool = False) -> pd.DataFrame:
    dataset_path = DATA_DIR / 'cdc_diabetes_health_indicators.csv'
    if dataset_path.exists() and not force_reload:
        return pd.read_csv(dataset_path)
    seed_path = BASE_DIR / 'seed' / 'cdc_diabetes_health_indicators.csv'
    if seed_path.exists() and not force_reload:
        return pd.read_csv(seed_path)
    try:
        return _download_dataset_csv(dataset_path)
    except Exception as exc:  # pragma: no cover - UX and network errors
        raise RuntimeError(
            'Não foi possível baixar o dataset do UCI automaticamente. '
            'Verifique a conexão com a internet ou adicione manualmente o CSV em '
            f'{dataset_path.parent}. Detalhe: {exc}'
        ) from exc


def _build_model_artifact(df: pd.DataFrame, *, target_col: str, drop_columns: Sequence[str], time_budget: int, metric: str,
                          estimator_list: Sequence[str], random_state: int, test_size: float, use_ensemble: bool) -> tuple[dict, list[str]]:
    from flaml.automl import AutoML
    from sklearn.model_selection import train_test_split

    if target_col not in df.columns:
        raise ValueError(f'A coluna alvo {target_col} não foi encontrada no dataset.')
    if not isinstance(drop_columns, (list, tuple)):
        drop_columns = list(drop_columns)
    X = prepare_feature_frame(df, target_col=target_col, drop_candidates=drop_columns)
    y = df[target_col].copy()
    if y.nunique() < 2:
        raise ValueError(f'A coluna alvo {target_col} precisa ter pelo menos duas classes para treino.')
    if X.empty:
        raise ValueError('A matriz de features ficou vazia. Revise as colunas removidas e o alvo selecionado.')

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.5,
        random_state=random_state,
        stratify=y_temp,
    )

    automl = AutoML()
    automl_settings = {
        'task': 'classification',
        'metric': metric,
        'time_budget': time_budget,
        'n_jobs': -1,
        'verbose': 0,
        'estimator_list': list(estimator_list),
        'ensemble': use_ensemble,
        'eval_method': 'holdout',
        'split_type': 'stratified',
    }
    automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)

    best_model_name = automl.best_estimator
    trained_model = getattr(automl.model, 'estimator', automl.model)
    if trained_model is None:
        raise RuntimeError('O FLAML não encontrou um estimador válido para o problema.')

    predictions = trained_model.predict(X_test)
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    metrics = {
        'accuracy': accuracy_score(y_test, predictions),
        'f1': f1_score(y_test, predictions),
        'roc_auc': float(roc_auc_score(y_test, trained_model.predict_proba(X_test)[:, 1])) if hasattr(trained_model, 'predict_proba') else None,
    }

    artifact = {
        'model': trained_model,
        'best_estimator_name': best_model_name,
        'feature_columns': list(X.columns),
        'target_col': target_col,
        'drop_columns': list(drop_columns),
        'metrics': metrics,
        'created_at': pd.Timestamp.utcnow().isoformat(),
    }
    return artifact, list(X.columns)


def save_model_artifact(artifact: dict, model_path: Path | None = None) -> Path:
    model_path = model_path or MODEL_DIR / 'cdc_diabetes_model.pkl'
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open('wb') as handle:
        pickle.dump(artifact, handle)
    return model_path


def load_model_artifact(model_path: Path | str | None = None) -> dict:
    artifact_path = resolve_model_path(model_path) or Path(model_path) if model_path else resolve_model_path() or MODEL_DIR / 'cdc_diabetes_model.pkl'
    with artifact_path.open('rb') as handle:
        return pickle.load(handle)


def predict_with_saved_model(model_path: Path | str | None, new_data: pd.DataFrame) -> pd.DataFrame:
    artifact = load_model_artifact(model_path)
    feature_cols = list(artifact.get('feature_columns', []) or [])
    if not feature_cols:
        raise ValueError('O artefato não informa as colunas esperadas pelo modelo.')
    frame = new_data.copy()
    if 'ID' in feature_cols and 'ID' not in frame.columns:
        frame['ID'] = 0
    missing = [col for col in feature_cols if col not in frame.columns]
    if missing:
        raise ValueError(f'Faltam colunas obrigatórias para predição: {missing}')

    X = frame[feature_cols].copy()
    model = artifact['model']
    predictions = model.predict(X)
    frame['predicted_diabetes'] = predictions
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(X)[:, 1]
        frame['probability_diabetes'] = probabilities
        if 'threshold' in artifact:
            frame['predicted_diabetes'] = (probabilities >= artifact['threshold']).astype(int)
    return frame


def build_ml_prediction_response(question: str, model_path: str | Path | None = None) -> str | None:
    resolved_path = resolve_model_path(model_path)
    if resolved_path is None:
        return None
    try:
        artifact = load_model_artifact(resolved_path)
    except Exception:
        return None

    feature_columns = list(artifact.get('feature_columns', []) or [])
    if not feature_columns:
        return None

    candidate_columns = [column for column in feature_columns if str(column).upper() != 'ID']
    payload = parse_prediction_payload(question, candidate_columns=candidate_columns)
    if not payload:
        return None

    missing = [column for column in candidate_columns if column not in payload]
    if missing:
        fields = ', '.join(missing[:5])
        return (
            'Posso fazer a predição, mas ainda faltam dados do paciente: '
            f'{fields}. Envie valores para essas variáveis e eu calculo o risco.'
        )

    frame = pd.DataFrame([payload])
    if 'ID' in feature_columns:
        frame['ID'] = 0
    frame = frame[feature_columns]
    result = predict_with_saved_model(resolved_path, frame)
    prediction = int(result['predicted_diabetes'].iloc[0])
    probability = float(result['probability_diabetes'].iloc[0]) if 'probability_diabetes' in result.columns else 0.0

    label = 'compatível com a classe positiva do dataset' if prediction == 1 else 'compatível com a classe negativa do dataset'
    chance = probability * 100
    return (
        f'Classificação do modelo ML: {label} (classe {prediction}). '
        f'Escore estimado para a classe positiva: {chance:.1f}%. '
        f"Limiar de classificação: {float(artifact.get('threshold', .5))*100:.0f}%. "
        'O alvo representa diabetes ou pré-diabetes no dataset; não é previsão de doença futura nem diagnóstico. '
        'Isso é apoio analítico educacional e não substitui avaliação clínica.'
    )


def render_ml_traditional() -> None:
    st.title('🧠 Modelo de ML · OXICOR')
    st.caption('Classificação educacional do alvo diabetes/pré-diabetes no dataset CDC. Sem diagnóstico ou previsão temporal individual.')
    active = resolve_model_path()
    if active:
        active_artifact = load_model_artifact(active)
        st.subheader('Modelo ativo no chat')
        st.write(active_artifact.get('best_estimator_name'))
        st.dataframe([{'métrica': k, 'valor': round(v,4)} for k,v in active_artifact.get('metrics',{}).items() if isinstance(v,(float,int))], hide_index=True)
        if 'threshold' in active_artifact:
            st.caption(f"Limiar: {active_artifact['threshold']:.0%}. Escolhido na validação; métricas acima calculadas no teste separado.")
            st.warning('A sensibilidade foi priorizada. A baixa precisão implica muitos falsos positivos; uso exclusivamente educacional.')

    try:
        dataset = load_cdc_dataset()
    except RuntimeError as exc:
        st.error(str(exc))
        st.info('Você pode baixar o CSV manualmente no UCI e salvar em data/cdc_diabetes_health_indicators.csv para continuar.')
        return
    metadata = load_metadata()
    default_drop = normalize_drop_columns(dataset.columns, DEFAULT_TARGET, metadata.get('drop_suggestions', []))

    st.subheader('1) Visão do dataset')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('Linhas', f'{len(dataset):,}')
    with col2:
        st.metric('Colunas', len(dataset.columns))
    with col3:
        st.metric('Alvo (diabetes)', f"{dataset[DEFAULT_TARGET].mean():.1%}")

    with st.expander('Descrição das colunas', expanded=False):
        descriptive_rows = []
        for column in dataset.columns:
            descriptive_rows.append({
                'coluna': column,
                'tipo': str(dataset[column].dtype),
                'descrição': COLUMN_DESCRIPTIONS.get(column, 'Descrição não cadastrada para esta coluna.'),
            })
        st.dataframe(pd.DataFrame(descriptive_rows), use_container_width=True)

    st.subheader('2) Preparação dos dados')
    selected_target = st.selectbox('Coluna alvo', options=[DEFAULT_TARGET] + [col for col in dataset.columns if col != DEFAULT_TARGET], index=0)
    drop_columns = st.multiselect(
        'Colunas sugeridas para remover',
        options=sorted(dataset.columns),
        default=normalize_drop_columns(dataset.columns, selected_target, default_drop),
        help='Remova variáveis de contexto, target e colunas que podem introduzir ruído ou viés no modelo.',
    )

    with st.expander('Sugestões de ciência de dados'):
        st.write('• Remova o target da matriz de features antes do treinamento.')
        st.write('• Considere quitar colunas de contexto social e de proxy, como Educação e Renda, quando o foco for risco clínico puro.')
        st.write('• Revise colunas altamente correlacionadas ou redundantes antes de comparar modelos.')
        st.write('• Sempre valide a distribuição do alvo em treino e teste para evitar viés de amostragem.')

    st.subheader('3) Hiperparâmetros do FLAML')
    params = st.columns(2)
    with params[0]:
        time_budget = st.slider('Time budget (segundos)', min_value=10, max_value=300, value=60, step=10)
        metric = st.selectbox('Métrica principal', options=['accuracy', 'f1', 'roc_auc', 'log_loss'], index=1)
        estimator_list = st.multiselect(
            'Estimadores permitidos',
            options=AVAILABLE_ESTIMATORS,
            default=['xgboost', 'lgbm', 'rf'],
        )
        if not estimator_list:
            st.warning('Selecione pelo menos um estimador para continuar.')
            return
    with params[1]:
        random_state = st.slider('Random state', min_value=0, max_value=100, value=42, step=1)
        test_size = st.slider('Tamanho do conjunto de teste', min_value=0.10, max_value=0.40, value=0.20, step=0.05)
        use_ensemble = st.checkbox('Usar ensemble FLAML', value=True)

    st.subheader('4) Treino e avaliação do modelo')
    if st.button('Treinar modelo FLAML', type='primary'):
        try:
            with st.spinner('Treinando e validando o modelo com FLAML...'):
                artifact, feature_columns = _build_model_artifact(
                    dataset,
                    target_col=selected_target,
                    drop_columns=drop_columns,
                    time_budget=time_budget,
                    metric=metric,
                    estimator_list=estimator_list,
                    random_state=random_state,
                    test_size=test_size,
                    use_ensemble=use_ensemble,
                )
            model_path = save_model_artifact(artifact)
            st.success(f'Modelo treinado com sucesso e salvo em: {model_path}')
            st.json({
                'melhor_estimador': str(type(artifact['model']).__name__),
                'feature_columns': feature_columns,
                'target': selected_target,
                'metrics': artifact['metrics'],
            })
            st.download_button(
                'Baixar modelo .pkl',
                data=pickle.dumps(artifact),
                file_name='cdc_diabetes_model.pkl',
                mime='application/octet-stream',
            )
            st.subheader('5) Teste com novos dados')
            uploaded_file = st.file_uploader('Carregue um CSV com novas amostras', type=['csv'])
            if uploaded_file is not None:
                new_data = pd.read_csv(uploaded_file)
                if set(feature_columns).issubset(new_data.columns):
                    predictions = predict_with_saved_model(model_path, new_data)
                    st.dataframe(predictions.head(20), use_container_width=True)
                    st.caption('A última coluna mostra a predição binária do modelo para cada linha do CSV enviado.')
                else:
                    missing = sorted(set(feature_columns) - set(new_data.columns))
                    st.warning(f'O CSV está faltando colunas obrigatórias: {missing}')
        except Exception as exc:  # pragma: no cover - feedback do usuário
            st.error(f'Erro durante o treino: {exc}')

    artifact_path = resolve_model_path() or MODEL_DIR / 'cdc_diabetes_model.pkl'
    if artifact_path.exists():
        st.subheader('6) Modelo já disponível no projeto')
        st.write(f'Arquivo atual: {artifact_path}')
        if st.button('Carregar modelo salvo para teste rápido'):
            try:
                artifact = load_model_artifact(artifact_path)
                st.json({
                    'modelo': str(type(artifact['model']).__name__),
                    'feature_columns': artifact['feature_columns'],
                    'target_col': artifact.get('target_col'),
                    'metrics': artifact.get('metrics'),
                })
            except Exception as exc:  # pragma: no cover
                st.error(f'Não foi possível abrir o arquivo salvo: {exc}')
