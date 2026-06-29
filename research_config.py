"""
research_config.py -- Dataset-specific research context for DataFlow AI.

Defines the research question, hypothesis, and domain metadata for known
sample datasets. Displayed in the UI to frame the analysis as a structured
data-science study rather than a generic upload.
"""

from __future__ import annotations

RESEARCH_CONTEXTS: dict[str, dict] = {
    "cs_training": {
        "title": "Financial Risk Prediction Study",
        "domain": "Financial Services / Credit Risk",
        "dataset": "Give Me Some Credit -- Kaggle (2011), 150,000 real borrower records",
        "n_subjects": 150_000,
        "research_question": (
            "Which financial behaviour patterns are the strongest predictors of serious "
            "loan delinquency (90+ days past due within 2 years), and can an automated "
            "pipeline deliver predictions that are both accurate and demographically fair?"
        ),
        "hypotheses": [
            "H1: Past payment delinquency history (NumberOfTimes90DaysLate, "
            "NumberOfTime30-59DaysPastDueNotWorse) will be the strongest predictors "
            "of financial distress as measured by SHAP global feature importance.",
            "H2: High revolving credit utilisation (RevolvingUtilizationOfUnsecuredLines > 0.5) "
            "combined with high debt ratio significantly increases default probability.",
            "H3: Gradient Boosting will outperform Logistic Regression in F1-score and MCC "
            "due to non-linear interactions between delinquency features.",
            "H4: After applying class_weight='balanced', the model will satisfy all four "
            "fairness criteria across age groups, with disparate impact ratio >= 0.80.",
        ],
        "target_column": "SeriousDlqin2yrs",
        "target_label_positive": "Serious delinquency within 2 years (1)",
        "target_label_negative": "No serious delinquency (0)",
        "sensitive_column": "age",
        "positive_label": 1,
        "feature_descriptions": {
            "SeriousDlqin2yrs": "TARGET -- person experienced 90+ days past due delinquency",
            "RevolvingUtilizationOfUnsecuredLines": "Revolving credit utilisation ratio (balance / limit)",
            "age": "Age of borrower in years -- SENSITIVE ATTRIBUTE for fairness analysis",
            "NumberOfTime30-59DaysPastDueNotWorse": "Times 30-59 days past due (not worse)",
            "DebtRatio": "Monthly debt payments / monthly gross income",
            "MonthlyIncome": "Borrower monthly income in USD (contains missing values)",
            "NumberOfOpenCreditLinesAndLoans": "Number of open loans and lines of credit",
            "NumberOfTimes90DaysLate": "Times 90+ days past due -- expected strongest predictor",
            "NumberRealEstateLoansOrLines": "Number of mortgage and real estate loans",
            "NumberOfTime60-89DaysPastDueNotWorse": "Times 60-89 days past due (not worse)",
            "NumberOfDependents": "Number of dependents (contains missing values)",
        },
        "expected_findings": [
            "NumberOfTimes90DaysLate and NumberOfTime30-59DaysPastDueNotWorse are expected "
            "to be top SHAP predictors -- confirming H1.",
            "High RevolvingUtilizationOfUnsecuredLines correlates strongly with default -- "
            "supporting H2.",
            "Gradient Boosting or Random Forest should outperform Logistic Regression "
            "on F1 and MCC -- supporting H3.",
            "Class-weighted training should improve fairness across age groups -- supporting H4.",
        ],
    },
    "heart_disease": {
        "title": "Heart Disease Prediction Study",
        "domain": "Clinical / Healthcare",
        "dataset": "Cleveland Heart Disease Dataset (UCI ML Repository, 1988)",
        "n_subjects": 303,
        "research_question": (
            "Which clinical and demographic factors are the strongest predictors "
            "of heart disease presence, and how accurately can a machine learning "
            "model classify patients at risk?"
        ),
        "hypotheses": [
            "H1: Exercise-induced angina (exang) and ST depression (oldpeak) are "
            "significantly associated with heart disease presence.",
            "H2: Maximum heart rate achieved (thalach) is negatively correlated with "
            "heart disease risk.",
            "H3: A Random Forest classifier will outperform Logistic Regression in "
            "predictive accuracy on this dataset.",
        ],
        "target_column": "target",
        "target_label_positive": "Heart disease present (1)",
        "target_label_negative": "No heart disease (0)",
        "sensitive_column": "sex",
        "positive_label": 1,
        "feature_descriptions": {
            "age": "Age of the patient (years)",
            "sex": "Sex (1 = male, 0 = female)",
            "cp": "Chest pain type (0=typical angina, 1=atypical, 2=non-anginal, 3=asymptomatic)",
            "trestbps": "Resting blood pressure (mmHg)",
            "chol": "Serum cholesterol (mg/dl)",
            "fbs": "Fasting blood sugar > 120 mg/dl (1=true, 0=false)",
            "restecg": "Resting ECG results",
            "thalach": "Maximum heart rate achieved (bpm)",
            "exang": "Exercise induced angina (1=yes, 0=no)",
            "oldpeak": "ST depression induced by exercise relative to rest",
            "slope": "Slope of peak exercise ST segment",
            "ca": "Number of major vessels coloured by fluoroscopy (0-3)",
            "thal": "Thalassemia type",
            "target": "Diagnosis of heart disease (1=present, 0=absent)",
        },
        "expected_findings": [
            "Chest pain type, maximum heart rate, and ST depression are expected top predictors.",
            "Male patients are expected to show higher disease prevalence.",
            "Tree-based models should outperform Logistic Regression due to non-linear interactions.",
        ],
    },
    "sample": {
        "title": "General Sample Dataset",
        "domain": "General",
        "dataset": "DataFlow AI sample dataset",
        "research_question": "Explore patterns, distributions and predictors in the dataset.",
        "hypotheses": [],
        "target_column": None,
        "sensitive_column": None,
        "positive_label": 1,
        "feature_descriptions": {},
        "expected_findings": [],
    },
}


def get_context(filename_stem: str) -> dict | None:
    return RESEARCH_CONTEXTS.get(filename_stem.lower().replace("-", "_").replace(" ", "_"))


def get_context_or_default(filename_stem: str) -> dict:
    return get_context(filename_stem) or {
        "title": "Data Science Analysis",
        "domain": "General",
        "dataset": filename_stem,
        "research_question": "Explore patterns and predictors in the uploaded dataset.",
        "hypotheses": [],
        "target_column": None,
        "sensitive_column": None,
        "positive_label": 1,
        "feature_descriptions": {},
        "expected_findings": [],
    }
