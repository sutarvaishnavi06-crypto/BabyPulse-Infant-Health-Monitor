import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


def detect_anomalies(df, contamination=0.05, n_estimators=100):
    if not 0.01 <= contamination <= 0.50:
        raise ValueError("Contamination must be between 0.01 and 0.50.")
    if not 10 <= n_estimators <= 500:
        raise ValueError("Number of estimators must be between 10 and 500.")
    numeric = df.select_dtypes(include="number").copy()
    if len(numeric) < 5:
        raise ValueError("At least 5 observations are required for anomaly detection.")
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna(axis=1, how="all")
    if numeric.shape[1] < 2:
        raise ValueError("The dataset must contain at least 2 usable numeric columns.")
    values = SimpleImputer(strategy="median").fit_transform(numeric)
    values = StandardScaler().fit_transform(values)
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=42
    )
    labels = model.fit_predict(values)
    scores = -model.decision_function(values)
    x_col, y_col = numeric.columns[:2]
    results = []
    for i in range(len(numeric)):
        results.append({
            "x": float(numeric.iloc[i, 0]),
            "y": float(numeric.iloc[i, 1]),
            "label": "Anomaly" if labels[i] == -1 else "Normal",
            "label_code": int(labels[i]),
            "score": round(float(scores[i]), 6)
        })
    anomaly_count = int((labels == -1).sum())
    return {
        "columns": [str(x_col), str(y_col)],
        "rows": len(numeric),
        "normal_count": int((labels == 1).sum()),
        "anomaly_count": anomaly_count,
        "anomaly_percentage": round(anomaly_count / len(numeric) * 100, 2),
        "results": results
    }
