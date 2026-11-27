"""Explain the frozen HELOC XGBoost model without retraining it."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit
import xgboost as xgb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.bundle
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['sha256'].items():
        if sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    if manifest['selected_model'] != 'XGB' or manifest['label_mapping'] != {'0': 'Good', '1': 'Bad'}:
        raise ValueError('Unexpected model or label mapping')
    model_path = root / manifest['selected_model_path']
    model = joblib.load(model_path)
    if list(model.classes_) != [0, 1]:
        raise ValueError('Unexpected model class order')
    test = pd.read_csv(root / 'data/test.csv')
    features = manifest['feature_order']
    X = test[features]
    matrix = xgb.DMatrix(X)
    booster = model.get_booster()
    # Native exact TreeSHAP in tree-path-dependent mode. The baseline is derived
    # from path cover statistics in the fitted model, not xai_background.csv.
    values = booster.predict(matrix, pred_contribs=True, approx_contribs=False)
    margins = booster.predict(matrix, output_margin=True)
    probabilities = model.predict_proba(X)[:, 1]
    residual = np.abs(values.sum(axis=1) - margins)
    probability_error = np.abs(expit(margins) - probabilities)
    stored = pd.read_csv(root / 'results/predictions.csv')
    stored = stored[(stored['model'] == 'XGB') & (stored['split'] == 'test')]
    comparison = test[['source_position', 'label']].merge(stored, on='source_position', validate='one_to_one', suffixes=('', '_stored'))
    if len(comparison) != len(test) or not np.array_equal(comparison['label'], comparison['label_stored']):
        raise ValueError('Test rows or labels disagree with saved predictions')
    prediction_error = np.max(np.abs(comparison['p_bad'] - probabilities))
    if max(float(residual.max()), float(probability_error.max()), float(prediction_error)) > 1e-5:
        raise ValueError('SHAP additivity or model prediction check failed')
    threshold = manifest['selected_threshold']
    predicted = probabilities >= threshold
    categories = {'true_bad': (test.label.to_numpy() == 1) & predicted,
                  'missed_bad': (test.label.to_numpy() == 1) & ~predicted,
                  'false_alarm': (test.label.to_numpy() == 0) & predicted}
    if any(not mask.any() for mask in categories.values()):
        raise ValueError('Expected representative categories are missing')
    args.output.mkdir(parents=True, exist_ok=False)
    pd.DataFrame({'feature': features, 'mean_abs_shap_log_odds': np.abs(values[:, :-1]).mean(axis=0)}).sort_values(
        'mean_abs_shap_log_odds', ascending=False).to_csv(args.output / 'global_importance.csv', index=False)
    pd.DataFrame(values[:, :-1], columns=features).assign(
        source_position=test.source_position, label=test.label, p_bad=probabilities,
        predicted_bad=predicted.astype(int), base_value=values[:, -1], margin=margins,
        additivity_error=residual).to_csv(args.output / 'test_shap.csv', index=False)
    examples = []
    for category, mask in categories.items():
        i = int(np.flatnonzero(mask)[0])
        explanation = {'method': 'xgboost_native_treeshap_tree_path_dependent', 'output_space': 'raw',
                       'base_value': float(values[i, -1]), 'model_output': float(margins[i]),
                       'feature_contributions': [{'feature': name, 'value': float(value)}
                                                 for name, value in zip(features, values[i, :-1], strict=True)]}
        examples.append({'category': category, 'source_position': int(test.iloc[i].source_position),
                         'true_label': int(test.iloc[i].label), 'threshold': threshold,
                         'dataset_id': manifest['dataset_id'],
                         'prediction': {'risk_probability': float(probabilities[i]),
                                        'model_version': 'heloc-standard-v1-xgb-2338',
                                        'model_artifact_sha256': sha256(model_path.read_bytes()).hexdigest()},
                         'explanation': explanation, 'shap_residual': float(residual[i])})
    (args.output / 'examples.json').write_text(json.dumps(examples, indent=2, allow_nan=False), encoding='utf-8')
    summary = {'model_sha256': sha256(model_path.read_bytes()).hexdigest(), 'xgboost_version': xgb.__version__,
               'method': 'exact native TreeSHAP, tree-path-dependent', 'background': 'training path cover in fitted model',
               'output_space': 'raw log-odds for Bad=1', 'test_rows': len(test), 'features': len(features),
               'threshold': threshold, 'max_additivity_error': float(residual.max()),
               'max_probability_error': float(probability_error.max()), 'max_saved_prediction_error': float(prediction_error),
               'categories': {k: int(v.sum()) for k, v in categories.items()},
               'examples': [{'category': e['category'], 'source_position': e['source_position']} for e in examples]}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
