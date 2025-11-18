# tools/train_model.py
import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

def make_synthetic_dataset(n=5000):
    rng = np.random.RandomState(42)
    request_rate = rng.poisson(50, n) + rng.normal(0,5,n)
    avg_latency = rng.normal(200,50,n)
    unique_users = np.maximum(1, (rng.poisson(5, n) + rng.normal(0,1,n)).astype(int))
    failed_logins = rng.binomial(3, 0.05, n)

    df = pd.DataFrame({
        "request_rate": request_rate,
        "avg_latency": avg_latency,
        "unique_users": unique_users,
        "failed_logins": failed_logins
    })

    # Inject small anomalies
    m = int(n * 0.02)
    df.iloc[:m] *= [5, 3, 2, 10]

    return df

def train_and_save(out):
    df = make_synthetic_dataset()
    features = df.values

    model = IsolationForest(
        n_estimators=100,
        contamination=0.02,
        random_state=42
    )
    model.fit(features)

    joblib.dump({
        "model": model,
        "columns": df.columns.tolist()
    }, out)

    print("Model saved to:", out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="models/model.pkl")
    args = parser.parse_args()
    train_and_save(args.out)
