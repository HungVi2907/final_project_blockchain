# Replication notes — Hlongwane et al. (2024)

> Historical reference only. The primary replication paper is now [Cheon et al., ICLR 2025](../PROJECT_CONTEXT.md).

For the verified full results and replication gaps, use [REPLICATION_AUDIT_VI.md](REPLICATION_AUDIT_VI.md). This earlier working note is retained for provenance.

Source paper: Hlongwane R, Ramabao K, Mongwe W, “A novel framework for enhancing transparency in credit scoring: Leveraging Shapley values for interpretable credit scorecards,” PLOS ONE 19(8), e0308718 (2024), https://doi.org/10.1371/journal.pone.0308718.

The open-access article PDF is saved beside this note. This is the authors’ ML/XAI method reference; it does not contain the Super Bells blockchain record verification experiments.

## Reported setup

- Taiwan: 30,000 records, 6,636 defaults (22.12%); Home Credit: 356,255 records, 24,845 defaults (6.97%).
- 80/20 train/test split. The paper does not clearly specify the random seed or split IDs, limiting exact numerical reproduction.
- Taiwan predictors were engineered from 23 original variables to 59; Home Credit used aggregations over related tables, expanding 217 variables to 767.
- Variable selection used permutation importance and Wald tests, retaining 7 Taiwan and 11 Home Credit variables; correlation threshold 0.8.
- Processing: binning numeric variables using WOE-oriented approach, one-hot encoding, mean imputation, clipping values at 2.5th/97.5th percentiles; grid search and five-fold CV.
- Models: Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost. SHAP values are then used to derive interpretable credit scorecards.

## Headline reported results

- Taiwan: Random Forest AUC 0.75929; XGBoost 0.75766; LightGBM 0.75690; CatBoost 0.74793. Logistic Regression AUC should be transcribed directly from Table 5 before use.
- Home Credit: XGBoost AUC 0.69766; LightGBM 0.69654; CatBoost 0.68450. Other values should be transcribed directly from Table 7 before use.
- These are the paper’s reported values, not reproduction targets guaranteed by matching metrics alone; the paper’s split seed and some processing details are not fixed sufficiently for bit-for-bit replication.

## Code availability status

No author code repository is linked from the paper page or identified by searches for the paper title, DOI, and author names. Treat code as not located so far, not proof that no private/unindexed code exists. The paper identifies public Taiwan UCI and Kaggle Home Credit datasets. Reimplementing the described pipeline is therefore required unless authors later provide code.

## Smoke replication plan

Start with Taiwan only: reproduce the paper's 80/20 split and stated feature engineering, binning/encoding, imputation, clipping, model families available in this environment, then compare AUC to the paper. Record deviations (seed, binning implementation, feature selection, libraries) and runtime. Only after smoke methodology and metric extraction are reviewed should the full Taiwan and Home Credit runs begin. Do not label the current LR baseline smoke as this replication.
