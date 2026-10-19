"""Treino reproduzível: python train_reproducible.py [CSV] [diretório de saída]."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
import sys
import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

def main():
    source = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/cdc_diabetes_health_indicators.csv')
    output = Path(sys.argv[2] if len(sys.argv) > 2 else 'data/models/etapa2')
    output.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(source)
    drop = ['ID', 'Diabetes_binary', 'Education', 'Income']
    X = df.drop(columns=drop)
    y = df.Diabetes_binary.astype(int)
    # Perfis iguais permanecem na mesma partição, mesmo quando seus alvos diferem.
    groups = pd.util.hash_pandas_object(X, index=False).to_numpy()
    train, rest = next(GroupShuffleSplit(n_splits=1, test_size=.30, random_state=42).split(X, y, groups))
    val_local, test_local = next(GroupShuffleSplit(n_splits=1, test_size=.5, random_state=43).split(X.iloc[rest], y.iloc[rest], groups[rest]))
    val, test = rest[val_local], rest[test_local]
    model = HistGradientBoostingClassifier(max_iter=120, max_leaf_nodes=15, learning_rate=.08, l2_regularization=1., early_stopping=False, random_state=42)
    print('Treinando', len(train), 'validação', len(val), 'teste', len(test), flush=True)
    model.fit(X.iloc[train], y.iloc[train])
    pv = model.predict_proba(X.iloc[val])[:, 1]
    # Objetivo educacional: recall >= .80 na validação, maximizando precision.
    candidates = []
    for threshold in np.arange(.05, .501, .01):
        predicted = pv >= threshold
        recall = recall_score(y.iloc[val], predicted)
        if recall >= .80:
            candidates.append((precision_score(y.iloc[val], predicted, zero_division=0), float(threshold), float(recall)))
    if not candidates:
        raise RuntimeError('Nenhum limiar alcançou o recall proposto na validação.')
    vp, threshold, vr = max(candidates)
    probability = model.predict_proba(X.iloc[test])[:, 1]
    predicted = probability >= threshold
    metrics = dict(accuracy=float(accuracy_score(y.iloc[test], predicted)), precision=float(precision_score(y.iloc[test], predicted)), recall=float(recall_score(y.iloc[test], predicted)), f1=float(f1_score(y.iloc[test], predicted)), roc_auc=float(roc_auc_score(y.iloc[test], probability)))
    metadata = dict(created_at=datetime.now(timezone.utc).isoformat(), dataset_name='CDC Diabetes Health Indicators', source_url='https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators', dataset_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), records=len(df), positive_records=int(y.sum()), target_col='Diabetes_binary', feature_columns=list(X.columns), drop_columns=drop, best_estimator_name='HistGradientBoostingClassifier', threshold=threshold, threshold_rule='Maior precision entre limiares 0.05..0.50 com recall >=0.80 na validação; passo 0.01.', validation_precision=vp, validation_recall=vr, split_method='GroupShuffleSplit por hash do perfil sem ID, alvo, Education e Income; sementes 42 e 43.', split_counts=dict(train=len(train), validation=len(val), test=len(test)), split_positive_counts=dict(train=int(y.iloc[train].sum()), validation=int(y.iloc[val].sum()), test=int(y.iloc[test].sum())), metrics=metrics, confusion_matrix=confusion_matrix(y.iloc[test], predicted).tolist(), sklearn_version=sklearn.__version__, model_parameters=model.get_params(), limitations=['Classificação do alvo observado, sem horizonte de previsão futura.', 'Dados de inquérito dos EUA; sem validação externa ou calibração para a população brasileira.', 'Limiar educacional privilegia sensibilidade; não é um limiar clínico.'])
    (output/'metrics.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output/'cdc_diabetes_model.pkl').open('wb') as handle:
        pickle.dump(dict(metadata, model=model), handle)
    np.savez_compressed(output/'split_indices.npz', train=train, validation=val, test=test)
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__':
    main()
