from pathlib import Path

import joblib
import pandas as pd

from sqlalchemy.orm import Session

from backend.database.models import Asset

from backend.ml.features import (
    get_asset_features,
)


BASE_DIR = Path(__file__).resolve().parent

MODEL_FILE = (
    BASE_DIR
    / "models"
    / "asset_risk_model.joblib"
)


def load_model():

    if not MODEL_FILE.exists():

        raise FileNotFoundError(
            (
                "Trained ML model not found. "
                "Run: python -m backend.ml.train_model"
            )
        )

    return joblib.load(
        MODEL_FILE
    )


def probability_to_level(
    probability: float,
) -> str:

    if probability >= 0.80:
        return "CRITICAL"

    if probability >= 0.60:
        return "HIGH"

    if probability >= 0.35:
        return "MEDIUM"

    return "LOW"


def predict_asset_risk(
    db: Session,
    asset: Asset,
) -> dict:

    bundle = load_model()

    model = bundle["model"]

    feature_names = bundle[
        "feature_names"
    ]

    # --------------------------------------------------------
    # Current database features
    # --------------------------------------------------------

    features = get_asset_features(
        db=db,
        asset=asset,
    )

    feature_vector = [
        features[name]
        for name in feature_names
    ]

    X = pd.DataFrame(
        [feature_vector],
        columns=feature_names,
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    prediction = int(
        model.predict(X)[0]
    )

    probabilities = (
        model.predict_proba(X)[0]
    )

    classes = (
        list(model.classes_)
    )

    probability_map = {
        int(cls): float(prob)
        for cls, prob in zip(
            classes,
            probabilities,
        )
    }

    high_risk_probability = (
        probability_map.get(
            1,
            0.0,
        )
    )

    risk_level = (
        probability_to_level(
            high_risk_probability
        )
    )

    return {
        "asset_id": asset.asset_id,
        "asset_code": asset.asset_code,
        "asset_type": asset.asset_type,
        "section_id": asset.section_id,

        "ml_prediction": prediction,

        "ml_risk_probability": round(
            high_risk_probability,
            4,
        ),

        "ml_risk_percentage": round(
            high_risk_probability * 100,
            2,
        ),

        "ml_risk_level": risk_level,

        "model": {
            "type": bundle.get(
                "model_type"
            ),
            "training_source": bundle.get(
                "training_source"
            ),
            "validation_accuracy": round(
                bundle.get(
                    "accuracy",
                    0,
                ),
                4,
            ),
        },

        "features": features,
    }


def predict_all_asset_risks(
    db: Session,
) -> list[dict]:

    assets = (
        db.query(Asset)
        .filter(
            Asset.status == "ACTIVE"
        )
        .order_by(
            Asset.asset_id
        )
        .all()
    )

    results = [
        predict_asset_risk(
            db=db,
            asset=asset,
        )
        for asset in assets
    ]

    return sorted(
        results,
        key=lambda item: (
            item[
                "ml_risk_probability"
            ],
            item["asset_id"],
        ),
        reverse=True,
    )