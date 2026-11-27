"""Anchor prepared retrained XGBoost explanations to a local Anvil registry."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from credit_audit.records import create_record
from heloc_pilot import register


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--examples', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18545)
    args = parser.parse_args()
    examples = json.loads(args.examples.read_text(encoding='utf-8'))
    args.output.mkdir(parents=True, exist_ok=False)
    summaries = []
    for example in examples:
        record, raw = create_record(example['dataset_id'], example['prediction'], example['explanation'])
        run = argparse.Namespace(port=args.port, output=args.output / example['category'])
        result = register(run, record, raw)
        summary = {'run_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                   'category': example['category'], 'source_position': example['source_position'],
                   'decision_id': record['decision_id'], 'dataset_id': record['dataset_id'],
                   'schema_version': record['schema_version'], 'model_version': record['model_version'],
                   'model_artifact_sha256': record['model_artifact_sha256'],
                   'risk_probability': record['risk_probability'], 'features_explained': 43,
                   'shap_residual': example['shap_residual']} | result
        (run.output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        summaries.append({k: summary[k] for k in ['category', 'source_position', 'risk_probability', 'verification',
                                                    'altered_copy_verification', 'gas_used', 'confirmation_ms']})
    (args.output / 'summary.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
