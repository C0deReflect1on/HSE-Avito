from pathlib import Path
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression


MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"


def _load_model(path: Path | str = MODEL_PATH) -> LogisticRegression:
    """Return the serialized model from disk."""
    with Path(path).open("rb") as handle:
        return pickle.load(handle)


def train_model() -> LogisticRegression:
    """Train a simple logistic regression on synthetic data."""
    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = ((X[:, 0] < 0.3) & (X[:, 1] < 0.2)).astype(int)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model


def save_model(model: LogisticRegression, path: Path | str = MODEL_PATH) -> None:
    """Persist the trained model to disk."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("wb") as handle:
        pickle.dump(model, handle)


def get_model(path: Path | str = MODEL_PATH) -> LogisticRegression:
    """Return a trained model, loading it from disk when available."""
    if Path(path).is_file():
        return _load_model(path)
    model = train_model()
    save_model(model, path)
    return model
