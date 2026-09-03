from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
)
from sklearn.model_selection import train_test_split

from backend.ml.dataset import (
    DATA_FILE,
    save_training_dataset,
)
from backend.ml.features import (
    FEATURE_NAMES,
)


BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models"

MODEL_FILE = (
    MODEL_DIR
    / "asset_risk_model.joblib"
)


def train_model():

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Make sure dataset exists
    # --------------------------------------------------------

    if not DATA_FILE.exists():

        dataset = save_training_dataset()

    else:

        dataset = pd.read_csv(
            DATA_FILE
        )

    # --------------------------------------------------------
    # Features and target
    # --------------------------------------------------------

    X = dataset[
        FEATURE_NAMES
    ]

    y = dataset["risk_label"]

    # --------------------------------------------------------
    # Train/test split
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y,
        )
    )

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(
        X_train,
        y_train,
    )

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    print(
        "\n=============================="
    )

    print(
        "ASSET RISK ML MODEL"
    )

    print(
        "=============================="
    )

    print(
        f"Training samples: {len(X_train)}"
    )

    print(
        f"Testing samples: {len(X_test)}"
    )

    print(
        f"Accuracy: {accuracy:.4f}"
    )

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    # --------------------------------------------------------
    # Save model + metadata
    # --------------------------------------------------------

    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "model_type": "RandomForestClassifier",
        "training_source": (
            "Synthetic prototype training data"
        ),
        "accuracy": float(accuracy),
    }

    joblib.dump(
        bundle,
        MODEL_FILE,
    )

    print(
        f"\nModel saved to:"
    )

    print(
        MODEL_FILE
    )

    return bundle


if __name__ == "__main__":
    train_model()