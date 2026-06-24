# Methodology

**DataFlow AI — Automated Data-Science Pipeline**
B.Sc. Data Science Final Year Project · Lebanese University

This document describes the data-science methodology implemented by the system,
in the order the pipeline executes it. It is written so that each step can be
independently justified and reproduced.

---

## 1. Data Ingestion and Profiling

The dataset is loaded into a `pandas` DataFrame (`utils/file_handler.py`). The
profiler (`ml/eda.profile_dataset`) records the structural characteristics that
condition every later decision:

- shape (rows × columns) and in-memory footprint;
- the split between numeric, categorical and datetime features;
- the proportion of missing cells;
- the number and proportion of duplicate rows.

A numeric column with very few distinct values (≤ 20) is treated as a categorical
label rather than a continuous variable — this prevents, for example, an encoded
0/1 outcome from being scaled and correlated as if it were continuous.

## 2. Data Preparation

Cleaning (`agents/cleaning_agent.py`) is **deterministic and audited** — every
action is logged and reported to the user:

- rows and columns that are entirely empty are dropped;
- exact duplicate rows are removed;
- text fields are whitespace-trimmed;
- **missing numeric values are imputed with the column median** (robust to
  outliers, unlike the mean);
- **missing categorical values are imputed with the column mode.**

Median/mode imputation is chosen over deletion to preserve sample size, and over
mean imputation to avoid distortion from skewed distributions.

## 3. Exploratory Data Analysis (`ml/eda.py`)

### 3.1 Descriptive statistics
For each numeric feature the system reports the standard five-number summary
plus three measures that a naive `describe()` omits:

- **Coefficient of variation** (σ/μ) — relative dispersion, comparable across
  features on different scales.
- **Skewness** — distribution asymmetry. |skew| > 1 is flagged, because strong
  skew motivates a transformation (e.g. log) before linear modelling.
- **Excess kurtosis** — tail heaviness relative to the normal distribution.

### 3.2 Categorical structure
For each categorical feature: cardinality, mode and its frequency, and the
**Shannon entropy** (in bits) of the value distribution, which quantifies how
evenly spread the categories are.

### 3.3 Outlier detection
Two complementary rules are reported per numeric feature:

- **IQR rule** — values outside [Q1 − 1.5·IQR, Q3 + 1.5·IQR];
- **z-score rule** — values more than 3 standard deviations from the mean.

Reporting both avoids over-reliance on a single definition (the z-score rule
assumes approximate normality; the IQR rule does not).

### 3.4 Correlation
A correlation matrix (Pearson by default; Spearman available for monotonic,
non-linear relationships) is computed, and the strongest pairwise correlations
are ranked by absolute value.

## 4. Inferential Statistics (`ml/statistics.py`)

EDA describes the *sample*; inferential tests ask whether a pattern is likely to
hold in the *population* or is plausibly noise. Every test reports its statistic,
p-value and a verdict at α = 0.05.

| Question | Test | Notes |
|---|---|---|
| Is a feature normally distributed? | Shapiro-Wilk (n ≤ 5000), else D'Agostino-Pearson | Shapiro-Wilk is unreliable on large samples, hence the switch. |
| Is a correlation real? | Pearson / Spearman with p-value | Filters spurious correlations. |
| Do group means differ? (2 groups) | Welch's t-test | Does not assume equal variances. |
| Do group means differ? (3+ groups) | One-way ANOVA (F-test) | |
| Are two categoricals associated? | Chi-square test of independence + Cramér's V | Cramér's V gives effect size, not just significance. |

### 4.1 Automatic feature–target screening
`feature_target_screen` selects the correct test for every feature against a
chosen target based on the (numeric / categorical) type of each, then ranks
features by p-value. This produces a defensible, statistically grounded shortlist
of candidate predictors **before** any model is trained.

## 5. Supervised Machine Learning (`ml/modeling.py`)

### 5.1 Task detection
The target's type and cardinality determine the task: a categorical target, or a
numeric target with ≤ 20 distinct values, is treated as **classification**;
otherwise **regression**. Identifier-like columns (near-unique, or named `*_id`)
are automatically excluded from the feature set to prevent leakage and trivial
memorisation.

### 5.2 Preprocessing (leakage-safe)
A scikit-learn `ColumnTransformer` is fitted **inside** the training pipeline so
that all statistics are learned from training data only:

- numeric features: median imputation → standardisation (`StandardScaler`);
- categorical features: mode imputation → one-hot encoding with
  `handle_unknown="ignore"` (so unseen test-time categories do not break
  inference).

### 5.3 Model training and selection
Three models per task are trained, spanning a linear baseline and two ensembles:

- **Classification:** Logistic Regression, Random Forest, Gradient Boosting.
- **Regression:** Linear Regression, Random Forest, Gradient Boosting.

Each model is assessed with **k-fold cross-validation** on the training split
(k adapts to the smallest class size for stratified classification), and then on
a **held-out test set** (20%, stratified for classification). Reporting both
cross-validation mean ± std and held-out scores lets the reader judge variance
and over-fitting, not just a single point estimate.

### 5.4 Evaluation metrics

- **Classification:** accuracy, precision, recall, F1 (weighted, so the metric
  is valid for imbalanced and multi-class problems), ROC-AUC, and a confusion
  matrix for the best model.
- **Regression:** R², RMSE, MAE.

The best model is selected by the held-out primary metric (F1 for
classification, R² for regression).

### 5.5 Feature importance
Importance is estimated with **permutation importance** on the held-out test
set: each feature is randomly shuffled and the resulting drop in score is
measured. This is model-agnostic (works for linear and tree models alike) and,
because it is measured on unseen data, reflects genuine predictive contribution
rather than in-sample fit.

### 5.6 Model diagnostics (`ml/diagnostics.py`)
A single accuracy number is not enough to trust a model. The platform also
reports:

- **ROC and precision-recall curves** with AUC / average precision (per class
  for multi-class problems via one-vs-rest), computed on the held-out set.
- **Hyper-parameter tuning** with `GridSearchCV`, reporting the default vs tuned
  cross-validated score and the chosen parameters.
- **Learning curves** (score vs training-set size for both training and
  cross-validation), which reveal over-fitting (a large train/CV gap) or
  under-fitting (both scores low and flat).

## 6. Unsupervised Learning (`ml/unsupervised.py`)

Beyond prediction, the platform searches for structure without labels.

### 6.1 Principal Component Analysis
After standardising the numeric features, PCA reduces dimensionality. The
explained-variance ratio of each component, the cumulative variance, the number
of components needed to retain 90% of the variance, and the feature loadings on
the first two components are reported, with a 2-D projection for visualisation.

### 6.2 KMeans clustering with automatic k
KMeans is run on the standardised features. The number of clusters is selected
**automatically** by choosing the value of k that maximises the mean
**silhouette score**, with the **inertia (elbow) curve** reported alongside.
The result includes per-cluster feature profiles and a PCA projection coloured
by cluster.

## 7. Feature Engineering & Selection (`ml/feature_engineering.py`)

A **univariate F-test** ranks features by their individual relationship to the
target, and **Recursive Feature Elimination** confirms this with a model-based
wrapper method. The **impact** of selection is quantified by comparing
cross-validated performance using all features versus the top-k, and a simple
**engineered interaction term** illustrates feature construction.

## 8. Statistical Rigor (`ml/statistics.py`)

- **Multiple-testing correction** (Bonferroni and Benjamini-Hochberg FDR).
- **Effect sizes** — Cohen's *d* and *eta-squared* — because significance is not
  the same as practical importance.
- **Confidence intervals** for means (t-distribution based).
- **Assumption checks** — normality (Shapiro-Wilk) and equal variance (Levene) —
  that recommend the correct test rather than applying one blindly.

## 9. Reporting

`agents/report_agent.py` assembles the computed profile, statistics, missing-value
analysis and significant correlations into a structured report. When an LLM is
configured, an executive summary and recommendations are added — but they are
explicitly constrained to interpret only the computed numbers.

## 10. Reproducibility and Limitations

- **Reproducibility:** a fixed random seed (42) governs all stochastic steps;
  no result depends on an LLM.
- **Limitations:** the modelling stage trains baseline models with default
  hyper-parameters (no tuning) and a single train/test split beyond
  cross-validation; the demo dataset is small (30 rows), so the sample models
  achieve near-perfect scores — on larger data the same pipeline yields more
  nuanced metrics. These are intentional scope boundaries, documented in the
  Future Work section of the README.

---

### Worked example (sample dataset)

On the bundled employee dataset, predicting `promoted`:

- the feature screen identifies `performance_score`, `satisfaction` and
  `salary` as the most strongly associated features (p < 1e-5);
- one-way ANOVA confirms salary differs significantly across departments
  (F ≈ 46.6, p ≈ 1.3e-10);
- a chi-square test confirms department and promotion are associated
  (χ² = 14.0, p ≈ 0.003, Cramér's V ≈ 0.68);
- the classifier recovers these as the top permutation-importance features,
  demonstrating consistency between the inferential and predictive stages.
