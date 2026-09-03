from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42
SAMPLES = 3000

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "training_data.csv"


FEATURE_COLUMNS = [
    "asset_age_years",
    "criticality_score",
    "open_defect_count",
    "highest_defect_severity",
    "active_task_count",
    "highest_task_severity",
    "days_overdue",
    "total_task_duration",
]


def generate_training_dataset(
    samples: int = SAMPLES,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    Generate synthetic historical-style railway
    maintenance records for ML prototype training.

    Important:
        This is synthetic prototype data.
        It is not real railway historical data.
    """

    if samples < 500:
        raise ValueError(
            "Training dataset should contain at least 500 samples."
        )

    rng = np.random.default_rng(seed)

    # ========================================================
    # 1. ASSET AGE
    # ========================================================

    asset_age_years = rng.integers(
        0,
        31,
        size=samples,
    )

    # ========================================================
    # 2. ASSET CRITICALITY
    # ========================================================

    criticality_score = rng.choice(
        [10, 25, 40, 50],
        size=samples,
        p=[
            0.15,   # LOW
            0.30,   # MEDIUM
            0.35,   # HIGH
            0.20,   # CRITICAL
        ],
    )

    # ========================================================
    # 3. OPEN DEFECT COUNT
    # ========================================================

    open_defect_count = rng.poisson(
        lam=0.8,
        size=samples,
    )

    open_defect_count = np.clip(
        open_defect_count,
        0,
        5,
    )

    # ========================================================
    # 4. HIGHEST DEFECT SEVERITY
    # ========================================================

    highest_defect_severity = []

    for count in open_defect_count:

        if count == 0:

            highest_defect_severity.append(0)

        else:

            severity = rng.choice(
                [5, 15, 25, 35],
                p=[
                    0.10,  # LOW
                    0.20,  # MEDIUM
                    0.40,  # HIGH
                    0.30,  # CRITICAL
                ],
            )

            highest_defect_severity.append(
                severity
            )

    highest_defect_severity = np.array(
        highest_defect_severity
    )

    # ========================================================
    # 5. ACTIVE TASK COUNT
    # ========================================================

    active_task_count = rng.poisson(
        lam=0.9,
        size=samples,
    )

    active_task_count = np.clip(
        active_task_count,
        0,
        5,
    )

    # ========================================================
    # 6. HIGHEST TASK SEVERITY
    # ========================================================

    highest_task_severity = []

    for count in active_task_count:

        if count == 0:

            highest_task_severity.append(0)

        else:

            severity = rng.choice(
                [5, 15, 25, 35],
                p=[
                    0.10,  # LOW
                    0.20,  # MEDIUM
                    0.40,  # HIGH
                    0.30,  # CRITICAL
                ],
            )

            highest_task_severity.append(
                severity
            )

    highest_task_severity = np.array(
        highest_task_severity
    )

    # ========================================================
    # 7. DAYS OVERDUE
    # ========================================================

    days_overdue = np.zeros(
        samples,
        dtype=int,
    )

    # Most tasks are not overdue.
    overdue_mask = (
        rng.random(samples) < 0.45
    )

    days_overdue[overdue_mask] = rng.integers(
        1,
        61,
        size=overdue_mask.sum(),
    )

    # ========================================================
    # 8. TOTAL TASK DURATION
    # ========================================================

    total_task_duration = np.zeros(
        samples
    )

    active_mask = (
        active_task_count > 0
    )

    total_task_duration[active_mask] = np.round(
        rng.uniform(
            0.5,
            8.0,
            size=active_mask.sum(),
        ),
        2,
    )

    # ========================================================
    # 9. SYNTHETIC RISK SIGNAL
    # ========================================================

    risk_signal = (
        # Asset characteristics
        asset_age_years * 1.8
        + criticality_score * 1.15

        # Defect pressure
        + open_defect_count * 10.0
        + highest_defect_severity * 1.35

        # Maintenance pressure
        + active_task_count * 6.0
        + highest_task_severity * 1.20

        # Overdue pressure
        + days_overdue * 0.75

        # Workload pressure
        + total_task_duration * 1.8
    )

    # ========================================================
    # 10. HIGH-RISK INTERACTIONS
    # ========================================================

    # Critical asset + critical defect
    risk_signal += np.where(
        (
            criticality_score >= 50
        )
        & (
            highest_defect_severity >= 35
        ),
        30,
        0,
    )

    # Critical task on highly critical asset
    risk_signal += np.where(
        (
            criticality_score >= 40
        )
        & (
            highest_task_severity >= 35
        ),
        25,
        0,
    )

    # Multiple defects
    risk_signal += np.where(
        open_defect_count >= 2,
        12,
        0,
    )

    # Severe overdue maintenance
    risk_signal += np.where(
        days_overdue >= 30,
        20,
        0,
    )

    # ========================================================
    # 11. REALISTIC VARIATION
    # ========================================================

    noise = rng.normal(
        loc=0,
        scale=8,
        size=samples,
    )

    risk_signal += noise

    # ========================================================
    # 12. BINARY RISK LABEL
    #
    # 0 = normal/lower risk
    # 1 = elevated/high risk
    # ========================================================

    risk_label = np.where(
        risk_signal >= 105,
        1,
        0,
    )

    # ========================================================
    # 13. BUILD DATAFRAME
    # ========================================================

    dataset = pd.DataFrame(
        {
            "asset_age_years": asset_age_years,
            "criticality_score": criticality_score,
            "open_defect_count": open_defect_count,
            "highest_defect_severity": (
                highest_defect_severity
            ),
            "active_task_count": active_task_count,
            "highest_task_severity": (
                highest_task_severity
            ),
            "days_overdue": days_overdue,
            "total_task_duration": (
                total_task_duration.round(2)
            ),
            "risk_label": risk_label,
        }
    )

    # ========================================================
    # 14. VALIDATION
    # ========================================================

    if dataset["risk_label"].nunique() < 2:
        raise ValueError(
            "Synthetic dataset contains only one class."
        )

    return dataset


def save_training_dataset() -> pd.DataFrame:
    """
    Generate and save the synthetic training dataset.
    """

    dataset = generate_training_dataset()

    dataset.to_csv(
        DATA_FILE,
        index=False,
    )

    return dataset


if __name__ == "__main__":

    df = save_training_dataset()

    print(
        f"Training dataset created: {DATA_FILE}"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        "\nClass distribution:"
    )

    print(
        df["risk_label"].value_counts()
    )

    print(
        "\nRisk percentage:"
    )

    print(
        (
            df["risk_label"].mean()
            * 100
        ).round(2),
        "%",
    )