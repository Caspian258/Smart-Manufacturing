"""
Módulo de análisis estadístico para el Dashboard Builder.
numpy + scipy + scikit-learn deben estar disponibles en el venv.
"""
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression


def compute_boxplot(values: list) -> dict | None:
    if not values or len(values) < 4:
        return None
    arr = np.array(values, dtype=float)
    q1, median, q3 = np.percentile(arr, [25, 50, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = arr[(arr < lower) | (arr > upper)].tolist()
    return {
        'min': float(np.min(arr[arr >= lower])) if arr[arr >= lower].size else float(q1),
        'q1': float(q1),
        'median': float(median),
        'q3': float(q3),
        'max': float(np.max(arr[arr <= upper])) if arr[arr <= upper].size else float(q3),
        'outliers': outliers,
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr)),
        'n': len(values),
    }


def compute_moving_average(values: list, window: int = 5) -> list:
    if not values:
        return []
    arr = np.array(values, dtype=float)
    result = np.convolve(arr, np.ones(window) / window, mode='valid')
    pad = [None] * (window - 1)
    return pad + result.tolist()


def compute_linear_regression(timestamps: list, values: list,
                               forecast_points: int = 12) -> dict | None:
    if not values or len(values) < 3:
        return None
    ts  = np.array(timestamps, dtype=float).reshape(-1, 1)
    vals = np.array(values, dtype=float)
    ts_norm = ts - ts[0]
    model = LinearRegression()
    model.fit(ts_norm, vals)
    trend = model.predict(ts_norm).tolist()
    r2 = float(model.score(ts_norm, vals))
    interval = float(np.mean(np.diff(ts.flatten()))) if len(ts) > 1 else 60.0
    future_ts = np.array([ts[-1][0] + interval * (i + 1) for i in range(forecast_points)])
    future_ts_norm = (future_ts - ts[0]).reshape(-1, 1)
    forecast = model.predict(future_ts_norm).tolist()
    slope_per_hour = float(model.coef_[0]) * 3600
    return {
        'trend_line': trend,
        'forecast_values': forecast,
        'forecast_timestamps': future_ts.tolist(),
        'r2': round(r2, 4),
        'slope_per_hour': round(slope_per_hour, 4),
        'direction': 'subiendo' if slope_per_hour > 0 else 'bajando',
    }


def detect_anomalies(values: list, method: str = 'zscore',
                     threshold: float = 2.5) -> dict:
    if not values or len(values) < 5:
        return {'anomalies': [], 'pct': 0, 'total': 0}
    arr = np.array(values, dtype=float)
    if method == 'zscore':
        z = np.abs(stats.zscore(arr))
        mask = z > threshold
    else:
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        mask = (arr < q1 - 1.5 * iqr) | (arr > q3 + 1.5 * iqr)
    indices = np.where(mask)[0].tolist()
    anomaly_values = arr[mask].tolist()
    return {
        'anomalies': [{'index': int(i), 'value': float(v)}
                      for i, v in zip(indices, anomaly_values)],
        'pct': round(len(indices) / len(values) * 100, 1),
        'total': len(indices),
    }


def compute_statistics(values: list) -> dict:
    if not values:
        return {}
    arr = np.array(values, dtype=float)
    mean = float(np.mean(arr))
    return {
        'mean':   round(mean, 3),
        'median': round(float(np.median(arr)), 3),
        'std':    round(float(np.std(arr)), 3),
        'min':    round(float(np.min(arr)), 3),
        'max':    round(float(np.max(arr)), 3),
        'range':  round(float(np.max(arr) - np.min(arr)), 3),
        'cv':     round(float(np.std(arr) / mean * 100), 2) if mean != 0 else 0,
        'n':      len(values),
    }
