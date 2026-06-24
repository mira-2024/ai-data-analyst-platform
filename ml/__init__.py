"""
ml — Data Science core for DataFlow AI.

This package contains the *computational* heart of the project. Unlike the
LLM agents (which narrate results in natural language), everything here is
real, reproducible data science implemented with pandas, NumPy, SciPy and
scikit-learn. No language model is required for any function in this package.

Modules
-------
eda         Exploratory Data Analysis: profiling, descriptive statistics,
            distribution shape, missingness, outlier detection, correlation.
statistics  Inferential statistics: normality tests, correlation significance,
            t-tests, one-way ANOVA, chi-square tests of independence, and an
            automatic feature-vs-target hypothesis screen.
modeling    Supervised machine-learning pipeline: task detection, preprocessing,
            model training with cross-validation, evaluation metrics and
            feature-importance estimation.
"""

from ml import eda, statistics, modeling

__all__ = ["eda", "statistics", "modeling"]
