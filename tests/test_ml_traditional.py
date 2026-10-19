import pandas as pd
import numpy as np


class StubPredictor:
    def predict(self, X):
        return [1] * len(X)

    def predict_proba(self, X):
        return np.array([[0.9, 0.1] for _ in range(len(X))])


from ml_traditional import (
    COLUMN_DESCRIPTIONS,
    AVAILABLE_ESTIMATORS,
    normalize_drop_columns,
    prepare_feature_frame,
    suggest_columns_to_remove,
)


def test_column_descriptions_are_defined_for_core_features():
    assert 'Diabetes_binary' in COLUMN_DESCRIPTIONS
    assert 'HighBP' in COLUMN_DESCRIPTIONS
    assert 'BMI' in COLUMN_DESCRIPTIONS
    assert 'Age' in COLUMN_DESCRIPTIONS


def test_suggest_columns_to_remove_includes_target_and_numeric_decision_features():
    suggestions = suggest_columns_to_remove()
    assert 'Diabetes_binary' in suggestions
    assert 'Education' in suggestions
    assert 'Income' in suggestions


def test_prepare_feature_frame_removes_target_and_drop_candidates():
    df = pd.DataFrame(
        {
            'Diabetes_binary': [0, 1, 0],
            'HighBP': [1, 0, 1],
            'HighChol': [0, 1, 1],
            'BMI': [25.5, 31.1, 27.9],
            'Education': [6, 4, 5],
            'Income': [8, 7, 6],
            'Age': [40, 60, 52],
        }
    )

    prepared = prepare_feature_frame(df, target_col='Diabetes_binary')
    assert 'Diabetes_binary' not in prepared.columns
    assert 'Education' not in prepared.columns
    assert 'Income' not in prepared.columns
    assert {'HighBP', 'HighChol', 'BMI', 'Age'} <= set(prepared.columns)


def test_normalize_drop_columns_keeps_target_and_removes_duplicates():
    columns = ['Diabetes_binary', 'HighBP', 'BMI', 'Education', 'Income']
    normalized = normalize_drop_columns(columns, 'Diabetes_binary', ['Diabetes_binary', 'Education', 'Education'])
    assert normalized == ['Diabetes_binary', 'Education']


def test_available_estimators_excludes_unavailable_catboost_option():
    assert 'catboost' not in AVAILABLE_ESTIMATORS
    assert {'xgboost', 'lgbm', 'rf', 'extra_tree'} <= set(AVAILABLE_ESTIMATORS)


def test_multi_agent_route_parser_accepts_only_known_route_labels():
    from multi_agents import parse_route

    assert parse_route('RAG') == 'RAG'
    assert parse_route('`DADOS`.') == 'DADOS'
    assert parse_route('ML\nextra text') == 'ML'
    assert parse_route('unknown route') == 'GERAL'


def test_parse_prediction_payload_extracts_numeric_and_boolean_features():
    from ml_traditional import parse_prediction_payload

    payload = parse_prediction_payload(
        'Paciente com BMI 31, pressão alta, colesterol alto, idade 52, fumante sim, renda 7, educação 5.'
    )

    assert payload['BMI'] == 31.0
    assert payload['HighBP'] == 1
    assert payload['HighChol'] == 1
    assert payload['Age'] == 52
    assert payload['Smoker'] == 1


def test_predict_with_saved_model_uses_placeholder_for_missing_id_column():
    from ml_traditional import predict_with_saved_model

    model = StubPredictor()

    artifact = {
        'model': model,
        'feature_columns': ['ID', 'BMI', 'Age'],
    }

    import pickle
    from pathlib import Path

    path = Path('tmp_test_model.pkl')
    with path.open('wb') as handle:
        pickle.dump(artifact, handle)

    try:
        frame = pd.DataFrame([{'BMI': 31, 'Age': 52}])
        result = predict_with_saved_model(path, frame)
        assert 'ID' in result.columns
        assert result['ID'].iloc[0] == 0
        assert result['predicted_diabetes'].iloc[0] == 1
    finally:
        path.unlink(missing_ok=True)
