# Implementation Readiness Supplement

## Purpose

The Week 3 report and proposal define the project's research direction, scope, main constraints, high-level workflow (S1-S11), selected technologies, and evaluation plan. They are sufficient to explain *what* the project is and why I1 is the proposed improvement.

They are not yet a complete implementation specification. This document records the decisions and artifacts that must be finalized before development starts, so that all team members implement the same system and experiments are reproducible.

## Confirmed Direction From Existing Documents

- The system is an experimental prototype, not a real loan-approval product.
- There are two independent ML pipelines: Home Credit Default Risk and UCI Taiwan Default of Credit Card Clients. Data and trained models must never be merged or transferred between those pipelines.
- Each dataset uses a stratified 70/15/15 train/validation/test split. All fitted preprocessing must use only its training split.
- Candidate models are Logistic Regression, Random Forest, and XGBoost. Model selection is based on validation metrics; the retained model is evaluated once on the corresponding test split.
- Predictions and local SHAP explanations are produced off-chain.
- I1 stores a complete pseudonymous decision record `R` off-chain, canonicalizes it, and computes `record_hash = SHA256(CanonicalSerialize(R))`.
- The Vyper registry stores only `decision_id`, `record_hash`, and `model_version_hash`; it must restrict writes to authorized writers.
- Verification recomputes both hashes from the persisted off-chain record and reports `VERIFIED`, `MISMATCH`, `NOT_FOUND`, or `PENDING`.
- Evaluation compares B0 (SQLite only), B1 (SQLite plus hash in the same database), and B2 (off-chain record plus on-chain commitment), with ML, SHAP, integrity, access-control, gas, and latency measurements.

## Gaps That Block Consistent Implementation

### 1. Reproducible Environment and Repository Layout

The technology names are specified, but exact versions and the repository structure are not.

Before coding, create and commit:

- A supported Python version and a locked dependency file (`pyproject.toml` plus lockfile, or `requirements.txt` with pinned versions).
- Exact versions for pandas, scikit-learn, XGBoost, SHAP, Web3.py, Vyper, Ape, pytest, Streamlit, and the Solidity/EVM tooling used by Ape.
- Node, Vyper, and Ape versions; Anvil version; Sepolia RPC provider choice.
- A `.env.example` containing names only, never secrets: `RPC_URL`, `PRIVATE_KEY`, `CHAIN_ID`, `CONTRACT_ADDRESS`, `SQLITE_PATH`.
- A repository layout separating `data/` (ignored), `src/`, `contracts/`, `tests/`, `scripts/`, `artifacts/` (ignored), and `docs/`.
- A fixed random seed policy for splitting, model training, and all sampled SHAP background data.

### 2. Data Contract and Leakage Controls

The sources and broad constraints are clear, but the concrete feature contract is not yet frozen.

Decide and document, per dataset:

- Download procedure, source URL, retrieval date, source-file names, and SHA-256 checksums.
- Target column, ID columns, final raw feature allow-list, and fields explicitly excluded.
- For Home Credit, the exact auxiliary tables to use (if any), their aggregation definitions, and a time-availability rule that prevents post-decision leakage.
- Duplicate-handling policy, missing-value policy, invalid-value rules, categorical encoding, numerical scaling, and outlier treatment.
- Class-imbalance treatment, including whether `class_weight`, resampling, or an untouched class distribution is used. Any resampling must occur only inside the training workflow.
- The split seed, split manifest format, and the persisted row identifiers for train/validation/test.

Deliverable: `docs/data_contract.md` plus versioned split manifests. Do not place raw personal or source data in Git.

### 3. ML Experiment Specification

The report names the candidate models and metrics but does not fix the runnable training protocol.

Specify:

- Hyperparameter search ranges, optimization metric, CV folds (if used), validation procedure, and model selection tie-breaker.
- Exact definition of Recall and F1, including the positive class and the operational threshold selection rule. A threshold may be selected on validation only.
- Confidence-interval method, resampling count, and random seed if confidence intervals are reported.
- Artifact format (`joblib` or equivalent), artifact directory convention, metadata file, and contents used to calculate `model_artifact_sha256`.
- A reproducible `train` command and an `evaluate` command that emit metrics, confusion matrix, selected threshold, and artifact metadata.

### 4. SHAP Contract

The records require SHAP outputs, but compatibility details must be fixed to avoid incompatible explanations.

Specify:

- The explainer for each supported model (`LinearExplainer`, `TreeExplainer`, or another supported alternative), versions, background-data selection, and sample-size cap.
- One declared `output_space` per model type: `probability` or raw margin. It must be stored in `R` and used consistently in the additivity test.
- Whether SHAP feature names refer to raw features or transformed features, and how one-hot encoded or aggregated features are mapped for display.
- Numerical tolerance for `base_value + sum(feature_contributions) ~= model_output`, calculated before decimal formatting.
- A failure policy: reject record creation, flag it, or store an explicit validation status when the additivity test fails.

### 5. Executable Canonical JSON Specification

The report gives strong rules for canonicalization, but it still needs an executable, testable contract.

Freeze the following before calculating production hashes:

- A JSON Schema for `R` with required fields, types, allowed dataset IDs, length limits, and a versioning policy.
- Whether every finite numeric value is converted to a string before serialization, including SHAP values and `risk_probability`; define rounding mode exactly (for example, decimal half-even or half-up).
- Exact treatment of negative zero, exponent notation, optional fields, `null`, booleans, arrays other than `feature_contributions`, escaping, and Unicode normalization failures.
- Exact `decision_id` representation (32 random bytes rendered as lowercase 64-character hexadecimal, or bytes32), and `nonce` length/encoding.
- The source-of-truth byte sequence: persist the canonical UTF-8 bytes at record creation and hash those bytes again at verification; do not regenerate time or nonce.

Deliverables:

- `schemas/decision_record_v1.schema.json`
- A single `canonical_serialize(record) -> bytes` implementation
- Golden vectors containing valid records, canonical bytes, expected `record_hash`, expected `model_version_hash`, and invalid-input cases

### 6. SQLite Persistence Contract

SQLite is chosen, but its schema and operational behavior are absent.

Define:

- Tables, primary keys, unique constraints, indexes, migration tool, and migration history.
- Whether canonical bytes are a BLOB and the JSON is retained separately for display; retain both only if their consistency is checked.
- Audit-log fields: creation time, transaction hash, chain ID, block number, confirmation status, verification result, and error reason.
- Duplicate `decision_id` handling and idempotency behavior when a client retries after a network failure.
- Local file location, backup/retention policy, and which artifacts must be excluded from Git.

### 7. Vyper Contract Specification and Deployment

The intended function names are listed, but the contract behavior must be made deployable and testable.

Complete the contract README and tests with:

- Storage structures and mappings, role model, constructor/initial admin, `grant_writer`, `revoke_writer`, and role-transfer policy.
- Full signatures, visibility, return types, event fields and indexed fields for `register_record`, `get_record`, and `verify_record_hash`.
- Revert conditions and messages/custom errors for unauthorized writes, zero hashes, duplicate IDs, and missing records.
- Immutability rule: registered commitments cannot be overwritten. If supersession is required later, define an explicit new decision/version rule rather than overwriting history.
- Network configuration for Anvil and Sepolia, deployment command, bytecode/compiler version, deployed address record, and minimum confirmation count before treating a transaction as confirmed.
- Unit tests for authorization, revoke behavior, duplicates, zero values, retrieval, verification, emitted events, and non-writer rejection.

### 8. Backend and Streamlit Interface Contract

The documents name Streamlit and Web3.py but do not define the boundary between UI, backend, database, and chain.

Define the following flows and data contracts:

- Input validation for a new assessment and selection of the allowed `dataset_id`/model artifact.
- Prediction -> SHAP -> record -> persist -> submit transaction -> confirmation -> verify sequence, including retry behavior.
- API/service methods or equivalent Python functions, request/response schemas, and status mapping for `PENDING`, `VERIFIED`, `MISMATCH`, `NOT_FOUND`, and transaction failure.
- UI screens: create assessment, assessment detail, transaction status, verify existing record, and an audit/error view.
- A rule that the UI must never label a record `VERIFIED` before sufficient chain confirmation and matching of both hashes.

### 9. Security, Privacy, and Operations

The project correctly excludes raw personal data from chain, but implementation controls are not yet concrete.

Specify:

- How private keys and RPC URLs are loaded only from local environment/secret storage; never commit them.
- Logging redaction rules for input profiles, SHAP values, hashes, and transaction metadata.
- Pseudonymous `input_reference` construction; it must not be a reversible personal identifier or plain applicant ID.
- Access-control assumptions for the SQLite file and dashboard.
- Failure and recovery behavior for unavailable SQLite, unavailable RPC, failed transaction, chain reorganization, and missing off-chain records.

### 10. Test Matrix and Definition of Done

The planned E1-E7 experiments are well scoped but need concrete test cases and pass criteria.

Implement:

- Unit tests for preprocessing leakage boundaries, split reproducibility, model-artifact hashing, SHAP additivity, canonical serialization, and database persistence.
- Smart-contract tests described in section 7.
- End-to-end tests for B0, B1, and B2, including a deliberate post-commit change to probability, SHAP contribution, and model version. Each must cause B2 verification to return `MISMATCH`.
- A test that modifying both the record and its SQLite-local hash does not defeat B2 verification.
- Golden-vector tests shared by Python and any other canonicalization implementation.
- A performance measurement protocol: hardware/network context, number of repetitions, warm-up policy, statistic reported (median and percentile recommended), and whether Anvil and Sepolia results are reported separately.
- CI that runs formatting, unit tests, contract tests, and golden vectors without using production secrets.

## Suggested Implementation Sequence

1. Freeze sections 1-5 and create the repository skeleton, schemas, dependency lockfile, and golden vectors.
2. Implement data loading, split manifests, preprocessing, model training, evaluation, and artifact hashing for one dataset first.
3. Implement SHAP and the full off-chain decision record, SQLite persistence, and local verification.
4. Implement and test the Vyper registry on Anvil.
5. Integrate Web3.py and Streamlit; exercise B0/B1/B2 end to end.
6. Repeat the independent ML pipeline for the second dataset.
7. Run E1-E7, record actual results separately from expected results, then deploy the demonstration contract to Sepolia if required.

## Minimum Ready-to-Implement Gate

Development should start only after the following are present and reviewed:

- [ ] Locked environments and `.env.example`
- [ ] Data contracts and split manifests
- [ ] Feature/preprocessing and leakage rules
- [ ] Training, threshold, and evaluation protocol
- [ ] SHAP output-space and additivity policy
- [ ] JSON Schema, canonicalization implementation, and golden vectors
- [ ] SQLite schema and migrations
- [ ] Vyper interface, role model, events, reverts, and tests
- [ ] Backend/UI state and error contract
- [ ] Security handling and automated test plan

## Important Scope Reminder

The on-chain commitment makes a stored decision record tamper-evident after confirmation. It does not establish that input data is truthful, the model prediction is correct or fair, SHAP is causal, or the off-chain store will remain available. These limits should remain visible in the final report and dashboard.
