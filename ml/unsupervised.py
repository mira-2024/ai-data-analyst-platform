"""
Unsupervised learning: dimensionality reduction (PCA) and clustering (KMeans).

Adds an unsupervised dimension to the platform. Both routines standardise the
numeric feature space first (PCA and KMeans are scale-sensitive), and the
number of clusters is chosen automatically via the silhouette score with the
elbow (inertia) curve reported alongside. Pure scikit-learn — deterministic
(fixed random_state), no language model involved.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ml import eda

RANDOM_STATE = 42


def _numeric_matrix(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Median-impute + standardise the numeric columns. Returns (X, columns)."""
    cols = eda.numeric_columns(df)
    # keep only columns with non-zero variance
    cols = [c for c in cols if df[c].nunique(dropna=True) > 1]
    if len(cols) < 2:
        return np.empty((0, 0)), []
    X = df[cols].to_numpy(dtype=float)
    X = SimpleImputer(strategy="median").fit_transform(X)
    X = StandardScaler().fit_transform(X)
    return X, cols


# ──────────────────────────────────────────────────────────────────────────────
# PCA
# ──────────────────────────────────────────────────────────────────────────────
def run_pca(df: pd.DataFrame, n_components: int | None = None) -> dict:
    """
    Principal Component Analysis over the standardised numeric features.

    Returns explained-variance ratios, cumulative variance, the components
    needed to reach 90% variance, the top feature loadings on PC1/PC2, and a 2-D
    projection (PC1, PC2) for plotting. Raises ValueError if < 2 usable columns.
    """
    X, cols = _numeric_matrix(df)
    if X.size == 0:
        raise ValueError("PCA needs at least 2 numeric columns with variance")

    max_comp = min(len(cols), X.shape[0])
    pca = PCA(n_components=n_components or max_comp, random_state=RANDOM_STATE)
    scores = pca.fit_transform(X)

    evr = pca.explained_variance_ratio_
    cum = np.cumsum(evr)
    n_for_90 = int(np.searchsorted(cum, 0.90) + 1)

    variance = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(evr))],
        "explained_variance": evr.round(4),
        "cumulative": cum.round(4),
    })

    # loadings (correlation of each feature with the component)
    loadings = pd.DataFrame(
        pca.components_[:2].T, index=cols,
        columns=["PC1", "PC2"][: pca.components_.shape[0]]
    ).round(4)

    projection = pd.DataFrame(scores[:, :2], columns=["PC1", "PC2"][: scores.shape[1]])

    return {
        "variance": variance,
        "n_components_for_90pct": n_for_90,
        "pc1_pct": round(float(evr[0]) * 100, 1),
        "pc2_pct": round(float(evr[1]) * 100, 1) if len(evr) > 1 else 0.0,
        "loadings": loadings,
        "projection": projection,
        "features_used": cols,
    }


# ──────────────────────────────────────────────────────────────────────────────
# KMeans clustering with automatic k
# ──────────────────────────────────────────────────────────────────────────────
def run_clustering(df: pd.DataFrame, k: int | None = None,
                   k_min: int = 2, k_max: int = 8) -> dict:
    """
    KMeans clustering on standardised numeric features.

    If ``k`` is None, scans k in [k_min, k_max] and picks the k that maximises
    the mean silhouette score; the inertia (elbow) and silhouette for every k
    are returned. Also returns the cluster assignment, per-cluster feature
    profiles (means in original units), and a 2-D PCA projection coloured by
    cluster. Raises ValueError if the data is too small.
    """
    X, cols = _numeric_matrix(df)
    if X.size == 0:
        raise ValueError("clustering needs at least 2 numeric columns with variance")
    n = X.shape[0]
    if n < 4:
        raise ValueError("need at least 4 rows to cluster")

    k_max = min(k_max, n - 1)
    selection_rows = []
    best_k, best_sil = (k or k_min), -1.0
    if k is None:
        for kk in range(k_min, k_max + 1):
            km = KMeans(n_clusters=kk, random_state=RANDOM_STATE, n_init=10)
            labels = km.fit_predict(X)
            sil = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else 0.0
            selection_rows.append({"k": kk, "inertia": round(float(km.inertia_), 2),
                                   "silhouette": round(sil, 4)})
            if sil > best_sil:
                best_sil, best_k = sil, kk

    final = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=10)
    labels = final.fit_predict(X)
    sil = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else 0.0

    # cluster profiles in original (un-scaled) units
    prof = df[cols].copy()
    prof["cluster"] = labels
    profiles = prof.groupby("cluster").mean(numeric_only=True).round(2)
    profiles.insert(0, "size", pd.Series(labels).value_counts().sort_index().values)

    # 2-D PCA projection coloured by cluster
    proj2d = PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X) \
        if len(cols) >= 2 else np.zeros((n, 2))
    projection = pd.DataFrame(proj2d, columns=["PC1", "PC2"])
    projection["cluster"] = labels.astype(str)

    return {
        "k": best_k,
        "silhouette": round(sil, 4),
        "labels": labels,
        "selection": pd.DataFrame(selection_rows),
        "profiles": profiles,
        "projection": projection,
        "features_used": cols,
    }
