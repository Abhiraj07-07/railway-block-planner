from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models import (
    Department,
    Station,
    Section,
    Asset,
    MaintenanceTask,
    Defect,
    Train,
    TrainSchedule,
    GoodsForecast,
)


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# EXPECTED FINAL DATASET
# ============================================================

EXPECTED_COUNTS = {
    "departments": 3,
    "stations": 5,
    "sections": 4,
    "assets": 6,
    "maintenance_tasks": 6,
    "defects": 3,
    "trains": 3,
    "train_schedule": 28,
    "goods_forecast": 28,
}


EXPECTED_START_DATE = "2026-09-02"
EXPECTED_END_DATE = "2026-09-08"


# ============================================================
# HELPERS
# ============================================================

def normalize_section_code(value) -> str:
    """
    Converts:
        1      -> SEC01
        2      -> SEC02
        SEC01  -> SEC01
    """

    section_code = str(value).strip()

    if section_code.upper().startswith("SEC"):
        return section_code.upper()

    return f"SEC{int(float(section_code)):02d}"


def normalize_text(value, default=""):
    """
    Safe string normalization.
    """

    if pd.isna(value):
        return default

    return str(value).strip()


def normalize_status(value, default="ACTIVE"):
    value = normalize_text(value, default)

    if not value:
        return default

    return value.upper()


def validate_required_file(filename: str):
    """
    Ensures a required CSV exists.
    """

    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {path}"
        )

    return path


def validate_date_range(dates, label: str):
    """
    Ensures source data uses the final planning horizon.
    """

    if not dates:
        raise ValueError(
            f"{label} contains no dates."
        )

    normalized_dates = sorted(
        str(value)
        for value in dates
    )

    if (
        normalized_dates[0] != EXPECTED_START_DATE
        or normalized_dates[-1] != EXPECTED_END_DATE
    ):
        raise ValueError(
            f"{label} date range is incorrect. "
            f"Expected {EXPECTED_START_DATE} to "
            f"{EXPECTED_END_DATE}, got "
            f"{normalized_dates[0]} to "
            f"{normalized_dates[-1]}."
        )


# ============================================================
# DATABASE RESET
# ============================================================

def reset_planner_data(db: Session):
    """
    Clears planner/source data while intentionally excluding
    authentication tables.

    No COMMIT is performed here. The caller controls the
    complete transaction.
    """

    print("\n🧹 Cleaning old railway planner data...\n")

    tables = [
        "block_tasks",
        "blocks",
        "operational_events",
        "train_schedule",
        "goods_forecast",
        "defects",
        "maintenance_tasks",
        "assets",
        "sections",
        "stations",
        "trains",
        "departments",
    ]

    table_list = ", ".join(tables)

    db.execute(
        text(
            f"""
            TRUNCATE TABLE {table_list}
            RESTART IDENTITY
            CASCADE
            """
        )
    )

    print("✅ Old planner data removed")
    print("✅ Authentication data was not directly targeted")


# ============================================================
# MAIN SEED FUNCTION
# ============================================================

def seed_data():

    db: Session = SessionLocal()

    try:

        print(
            "\n"
            "============================================================\n"
            "🚆 RAILWAY BLOCK PLANNER - COMPLETE DATA RESET + SEED\n"
            "============================================================\n"
        )

        # ====================================================
        # 0. RESET
        # ====================================================

        reset_planner_data(db)

        # ====================================================
        # 1. DEPARTMENTS
        # ====================================================

        departments = [
            Department(
                department_code="ENG",
                department_name="Engineering",
            ),
            Department(
                department_code="TRD",
                department_name="Traction Distribution",
            ),
            Department(
                department_code="SNT",
                department_name="Signal & Telecommunication",
            ),
        ]

        db.add_all(departments)
        db.flush()

        department_map = {
            department.department_code:
                department.department_id
            for department
            in db.query(Department).all()
        }

        print(
            f"✅ Departments inserted: "
            f"{len(departments)}"
        )

        # ====================================================
        # 2. STATIONS
        # ====================================================

        stations_path = validate_required_file(
            "stations.csv"
        )

        stations_df = pd.read_csv(
            stations_path
        )

        required_station_columns = {
            "station_code",
            "station_name",
        }

        missing = required_station_columns - set(
            stations_df.columns
        )

        if missing:
            raise ValueError(
                f"stations.csv missing columns: {missing}"
            )

        station_objects = []

        for _, row in stations_df.iterrows():

            station_objects.append(
                Station(
                    station_code=normalize_text(
                        row["station_code"]
                    ),
                    station_name=normalize_text(
                        row["station_name"]
                    ),
                )
            )

        if len(station_objects) != EXPECTED_COUNTS["stations"]:
            raise ValueError(
                f"Expected 5 stations, found "
                f"{len(station_objects)}."
            )

        db.add_all(station_objects)
        db.flush()

        station_map = {
            station.station_code:
                station.station_id
            for station
            in db.query(Station).all()
        }

        print(
            f"✅ Stations inserted: "
            f"{len(station_objects)}"
        )

        # ====================================================
        # 3. SECTIONS
        # ====================================================

        sections_path = validate_required_file(
            "sections.csv"
        )

        sections_df = pd.read_csv(
            sections_path
        )

        required_section_columns = {
            "section_code",
            "from_station",
            "to_station",
            "distance_km",
        }

        missing = required_section_columns - set(
            sections_df.columns
        )

        if missing:
            raise ValueError(
                f"sections.csv missing columns: {missing}"
            )

        section_objects = []

        for _, row in sections_df.iterrows():

            section_code = normalize_text(
                row["section_code"]
            ).upper()

            from_code = normalize_text(
                row["from_station"]
            )

            to_code = normalize_text(
                row["to_station"]
            )

            if from_code not in station_map:
                raise ValueError(
                    f"Unknown from_station: "
                    f"{from_code}"
                )

            if to_code not in station_map:
                raise ValueError(
                    f"Unknown to_station: "
                    f"{to_code}"
                )

            section_objects.append(
                Section(
                    section_code=section_code,

                    from_station_id=station_map[
                        from_code
                    ],

                    to_station_id=station_map[
                        to_code
                    ],

                    distance_km=float(
                        row["distance_km"]
                    ),

                    status="ACTIVE",
                )
            )

        if len(section_objects) != EXPECTED_COUNTS["sections"]:
            raise ValueError(
                f"Expected 4 sections, found "
                f"{len(section_objects)}."
            )

        db.add_all(section_objects)
        db.flush()

        section_map = {
            section.section_code:
                section.section_id
            for section
            in db.query(Section).all()
        }

        print(
            f"✅ Sections inserted: "
            f"{len(section_objects)}"
        )

        # ====================================================
        # 4. ASSETS
        # ====================================================

        assets_path = validate_required_file(
            "assets.csv"
        )

        assets_df = pd.read_csv(
            assets_path
        )

        required_asset_columns = {
            "asset_code",
            "asset_type",
            "section_id",
            "department",
            "criticality",
            "status",
        }

        missing = required_asset_columns - set(
            assets_df.columns
        )

        if missing:
            raise ValueError(
                f"assets.csv missing columns: {missing}"
            )

        department_lookup = {
            "Engineering": "ENG",
            "Traction": "TRD",
            "Traction Distribution": "TRD",
            "S&T": "SNT",
            "Signal & Telecommunication": "SNT",
        }

        asset_objects = []

        for _, row in assets_df.iterrows():

            department_name = normalize_text(
                row["department"]
            )

            department_code = department_lookup.get(
                department_name,
                department_name,
            )

            if department_code not in department_map:
                raise ValueError(
                    f"Unknown department: "
                    f"{department_name}"
                )

            section_code = normalize_section_code(
                row["section_id"]
            )

            if section_code not in section_map:
                raise ValueError(
                    f"Unknown section: "
                    f"{section_code}"
                )

            asset_objects.append(
                Asset(
                    asset_code=normalize_text(
                        row["asset_code"]
                    ),

                    asset_type=normalize_text(
                        row["asset_type"]
                    ).upper(),

                    section_id=section_map[
                        section_code
                    ],

                    department_id=department_map[
                        department_code
                    ],

                    criticality=normalize_text(
                        row["criticality"]
                    ).upper(),

                    status=normalize_status(
                        row["status"],
                        "ACTIVE"
                    ),
                )
            )

        if len(asset_objects) != EXPECTED_COUNTS["assets"]:
            raise ValueError(
                f"Expected 6 assets, found "
                f"{len(asset_objects)}."
            )

        db.add_all(asset_objects)
        db.flush()

        asset_map = {
            asset.asset_code:
                asset.asset_id
            for asset
            in db.query(Asset).all()
        }

        print(
            f"✅ Assets inserted: "
            f"{len(asset_objects)}"
        )

        # ====================================================
        # 5. MAINTENANCE TASKS
        # ====================================================

        maintenance_files = [
            ("tms_tasks.csv", "TMS", "ENG"),
            ("smms_tasks.csv", "SMMS", "SNT"),
            ("tdms_tasks.csv", "TDMS", "TRD"),
        ]

        maintenance_objects = []

        for filename, source_system, department_code in maintenance_files:

            file_path = validate_required_file(
                filename
            )

            df = pd.read_csv(file_path)

            required_columns = {
                "task_id",
                "asset_code",
                "section_id",
                "task_type",
                "severity",
                "duration_hours",
                "status",
                "due_date",
            }

            missing = required_columns - set(
                df.columns
            )

            if missing:
                raise ValueError(
                    f"{filename} missing columns: "
                    f"{missing}"
                )

            for _, row in df.iterrows():

                asset_code = normalize_text(
                    row["asset_code"]
                )

                if asset_code not in asset_map:
                    raise ValueError(
                        f"Unknown asset: "
                        f"{asset_code}"
                    )

                section_code = normalize_section_code(
                    row["section_id"]
                )

                if section_code not in section_map:
                    raise ValueError(
                        f"Unknown section: "
                        f"{section_code}"
                    )

                maintenance_objects.append(
                    MaintenanceTask(
                        task_code=normalize_text(
                            row["task_id"]
                        ),

                        source_system=source_system,

                        department_id=department_map[
                            department_code
                        ],

                        asset_id=asset_map[
                            asset_code
                        ],

                        section_id=section_map[
                            section_code
                        ],

                        task_type=normalize_text(
                            row["task_type"]
                        ),

                        severity=normalize_text(
                            row["severity"]
                        ).upper(),

                        duration_hours=float(
                            row["duration_hours"]
                        ),

                        status=normalize_text(
                            row["status"]
                        ).upper(),

                        due_date=pd.to_datetime(
                            row["due_date"]
                        ).date(),

                        description=(
                            f"{row['task_type']} "
                            f"imported from "
                            f"{source_system}"
                        ),
                    )
                )

        if len(maintenance_objects) != EXPECTED_COUNTS["maintenance_tasks"]:
            raise ValueError(
                f"Expected 6 maintenance tasks, found "
                f"{len(maintenance_objects)}."
            )

        db.add_all(maintenance_objects)
        db.flush()

        print(
            f"✅ Maintenance tasks inserted: "
            f"{len(maintenance_objects)}"
        )

        # ====================================================
        # 6. DEFECTS
        # ====================================================

        defects_path = validate_required_file(
            "defects.csv"
        )

        defects_df = pd.read_csv(
            defects_path
        )

        required_defect_columns = {
            "defect_id",
            "asset_code",
            "section_id",
            "severity",
            "description",
            "detected_date",
            "status",
        }

        missing = required_defect_columns - set(
            defects_df.columns
        )

        if missing:
            raise ValueError(
                f"defects.csv missing columns: {missing}"
            )

        defect_objects = []

        for _, row in defects_df.iterrows():

            asset_code = normalize_text(
                row["asset_code"]
            )

            if asset_code not in asset_map:
                raise ValueError(
                    f"Unknown asset: "
                    f"{asset_code}"
                )

            section_code = normalize_section_code(
                row["section_id"]
            )

            if section_code not in section_map:
                raise ValueError(
                    f"Unknown section: "
                    f"{section_code}"
                )

            defect_objects.append(
                Defect(
                    defect_code=normalize_text(
                        row["defect_id"]
                    ),

                    asset_id=asset_map[
                        asset_code
                    ],

                    section_id=section_map[
                        section_code
                    ],

                    severity=normalize_text(
                        row["severity"]
                    ).upper(),

                    description=normalize_text(
                        row["description"]
                    ),

                    detected_date=pd.to_datetime(
                        row["detected_date"]
                    ).date(),

                    status=normalize_text(
                        row["status"]
                    ).upper(),
                )
            )

        if len(defect_objects) != EXPECTED_COUNTS["defects"]:
            raise ValueError(
                f"Expected 3 defects, found "
                f"{len(defect_objects)}."
            )

        db.add_all(defect_objects)
        db.flush()

        print(
            f"✅ Defects inserted: "
            f"{len(defect_objects)}"
        )

        # ====================================================
        # 7. TRAINS
        # ====================================================

        trains_path = validate_required_file(
            "trains.csv"
        )

        trains_df = pd.read_csv(
            trains_path
        )

        required_train_columns = {
            "train_no",
            "train_name",
            "train_type",
            "priority",
        }

        missing = required_train_columns - set(
            trains_df.columns
        )

        if missing:
            raise ValueError(
                f"trains.csv missing columns: {missing}"
            )

        train_objects = []

        for _, row in trains_df.iterrows():

            train_objects.append(
                Train(
                    train_no=normalize_text(
                        row["train_no"]
                    ),

                    train_name=normalize_text(
                        row["train_name"]
                    ),

                    train_type=normalize_text(
                        row["train_type"]
                    ).upper(),

                    priority=normalize_text(
                        row["priority"]
                    ).upper(),
                )
            )

        if len(train_objects) != EXPECTED_COUNTS["trains"]:
            raise ValueError(
                f"Expected 3 trains, found "
                f"{len(train_objects)}."
            )

        db.add_all(train_objects)
        db.flush()

        train_by_id = {
            str(train.train_id):
                train
            for train
            in db.query(Train).all()
        }

        train_by_no = {
            train.train_no:
                train
            for train
            in db.query(Train).all()
        }

        print(
            f"✅ Trains inserted: "
            f"{len(train_objects)}"
        )

        # ====================================================
        # 8. TRAIN SCHEDULE
        # ====================================================

        schedule_path = validate_required_file(
            "train_schedule.csv"
        )

        schedule_df = pd.read_csv(
            schedule_path
        )

        required_schedule_columns = {
            "schedule_id",
            "train_id",
            "section_id",
            "date",
            "arrival_time",
            "departure_time",
        }

        missing = required_schedule_columns - set(
            schedule_df.columns
        )

        if missing:
            raise ValueError(
                f"train_schedule.csv missing columns: "
                f"{missing}"
            )

        if len(schedule_df) != EXPECTED_COUNTS["train_schedule"]:
            raise ValueError(
                f"Expected 28 train schedule rows, found "
                f"{len(schedule_df)}."
            )

        # Validate schedule IDs in source file
        schedule_ids = [
            int(value)
            for value in schedule_df["schedule_id"]
        ]

        if schedule_ids != list(range(1, 29)):
            raise ValueError(
                "train_schedule.csv schedule_id must "
                "contain exactly 1 to 28."
            )

        schedule_dates = sorted(
            pd.to_datetime(
                schedule_df["date"]
            )
            .dt.date
            .unique()
        )

        validate_date_range(
            schedule_dates,
            "train_schedule.csv"
        )

        schedule_objects = []

        for _, row in schedule_df.iterrows():

            train_identifier = normalize_text(
                row["train_id"]
            )

            matching_train = (
                train_by_id.get(
                    train_identifier
                )
                or train_by_no.get(
                    train_identifier
                )
            )

            if matching_train is None:
                raise ValueError(
                    f"Unknown train: "
                    f"{train_identifier}"
                )

            section_code = normalize_section_code(
                row["section_id"]
            )

            if section_code not in section_map:
                raise ValueError(
                    f"Unknown section: "
                    f"{section_code}"
                )

            arrival = pd.to_datetime(
                normalize_text(
                    row["arrival_time"]
                )
            ).time()

            departure = pd.to_datetime(
                normalize_text(
                    row["departure_time"]
                )
            ).time()

            # Correct railway schedule relationship:
            # departure must be at or after arrival.
            if departure < arrival:
                raise ValueError(
                    "Invalid train schedule: "
                    f"departure {departure} is before "
                    f"arrival {arrival} for "
                    f"schedule_id "
                    f"{row['schedule_id']}."
                )

            schedule_objects.append(
                TrainSchedule(
                    train_id=matching_train.train_id,

                    section_id=section_map[
                        section_code
                    ],

                    schedule_date=pd.to_datetime(
                        row["date"]
                    ).date(),

                    arrival_time=arrival,

                    departure_time=departure,
                )
            )

        db.add_all(schedule_objects)
        db.flush()

        print(
            f"✅ Train schedules inserted: "
            f"{len(schedule_objects)}"
        )

        # ====================================================
        # 9. GOODS FORECAST
        # ====================================================

        forecast_path = validate_required_file(
            "goods_forecast.csv"
        )

        forecast_df = pd.read_csv(
            forecast_path
        )

        required_forecast_columns = {
            "forecast_id",
            "section_id",
            "date",
            "expected_goods_trains",
        }

        missing = required_forecast_columns - set(
            forecast_df.columns
        )

        if missing:
            raise ValueError(
                f"goods_forecast.csv missing columns: "
                f"{missing}"
            )

        if len(forecast_df) != EXPECTED_COUNTS["goods_forecast"]:
            raise ValueError(
                f"Expected 28 goods forecast rows, found "
                f"{len(forecast_df)}."
            )

        forecast_ids = [
            int(value)
            for value in forecast_df["forecast_id"]
        ]

        if forecast_ids != list(range(1, 29)):
            raise ValueError(
                "goods_forecast.csv forecast_id must "
                "contain exactly 1 to 28."
            )

        forecast_dates = sorted(
            pd.to_datetime(
                forecast_df["date"]
            )
            .dt.date
            .unique()
        )

        validate_date_range(
            forecast_dates,
            "goods_forecast.csv"
        )

        forecast_objects = []

        for _, row in forecast_df.iterrows():

            section_code = normalize_section_code(
                row["section_id"]
            )

            if section_code not in section_map:
                raise ValueError(
                    f"Unknown section: "
                    f"{section_code}"
                )

            expected_goods = int(
                row["expected_goods_trains"]
            )

            if expected_goods < 0:
                raise ValueError(
                    f"Goods forecast cannot be negative: "
                    f"{expected_goods}"
                )

            forecast_objects.append(
                GoodsForecast(
                    section_id=section_map[
                        section_code
                    ],

                    forecast_date=pd.to_datetime(
                        row["date"]
                    ).date(),

                    expected_goods_trains=expected_goods,
                )
            )

        db.add_all(forecast_objects)
        db.flush()

        print(
            f"✅ Goods forecasts inserted: "
            f"{len(forecast_objects)}"
        )

        # ====================================================
        # 10. FINAL VALIDATION
        # ====================================================

        print(
            "\n🔎 Validating final database state...\n"
        )

        counts = {
            "Departments":
                db.query(Department).count(),

            "Stations":
                db.query(Station).count(),

            "Sections":
                db.query(Section).count(),

            "Assets":
                db.query(Asset).count(),

            "Maintenance Tasks":
                db.query(MaintenanceTask).count(),

            "Defects":
                db.query(Defect).count(),

            "Trains":
                db.query(Train).count(),

            "Train Schedules":
                db.query(TrainSchedule).count(),

            "Goods Forecasts":
                db.query(GoodsForecast).count(),
        }

        expected_named = {
            "Departments": 3,
            "Stations": 5,
            "Sections": 4,
            "Assets": 6,
            "Maintenance Tasks": 6,
            "Defects": 3,
            "Trains": 3,
            "Train Schedules": 28,
            "Goods Forecasts": 28,
        }

        validation_ok = True

        for name, actual in counts.items():

            expected = expected_named[name]

            if actual == expected:
                print(
                    f"✅ {name}: {actual}"
                )
            else:
                print(
                    f"❌ {name}: {actual} "
                    f"(expected {expected})"
                )

                validation_ok = False

        # ====================================================
        # SCHEDULE DATE VALIDATION
        # ====================================================

        schedule_date_rows = (
            db.query(
                TrainSchedule.schedule_date
            )
            .distinct()
            .order_by(
                TrainSchedule.schedule_date
            )
            .all()
        )

        schedule_dates_db = [
            row[0]
            for row
            in schedule_date_rows
        ]

        print(
            "\n📅 Train schedule dates:"
        )

        for date_value in schedule_dates_db:
            print(
                f"   • {date_value}"
            )

        if (
            str(schedule_dates_db[0])
            != EXPECTED_START_DATE
            or
            str(schedule_dates_db[-1])
            != EXPECTED_END_DATE
            or
            len(schedule_dates_db) != 7
        ):
            validation_ok = False

            print(
                "❌ Train schedule date range validation failed."
            )

        else:
            print(
                "✅ Train schedule date range validated."
            )

        # ====================================================
        # FORECAST DATE VALIDATION
        # ====================================================

        forecast_date_rows = (
            db.query(
                GoodsForecast.forecast_date
            )
            .distinct()
            .order_by(
                GoodsForecast.forecast_date
            )
            .all()
        )

        forecast_dates_db = [
            row[0]
            for row
            in forecast_date_rows
        ]

        print(
            "\n📦 Goods forecast dates:"
        )

        for date_value in forecast_dates_db:
            print(
                f"   • {date_value}"
            )

        if (
            str(forecast_dates_db[0])
            != EXPECTED_START_DATE
            or
            str(forecast_dates_db[-1])
            != EXPECTED_END_DATE
            or
            len(forecast_dates_db) != 7
        ):
            validation_ok = False

            print(
                "❌ Goods forecast date range validation failed."
            )

        else:
            print(
                "✅ Goods forecast date range validated."
            )

        # ====================================================
        # PER-DAY SCHEDULE COUNT
        # ====================================================

        schedule_distribution = (
            db.query(
                TrainSchedule.schedule_date
            )
            .all()
        )

        schedule_counts = {}

        for row in schedule_distribution:
            date_value = row[0]
            schedule_counts[date_value] = (
                schedule_counts.get(
                    date_value,
                    0
                ) + 1
            )

        print(
            "\n📊 Schedule rows per day:"
        )

        for date_value in sorted(
            schedule_counts
        ):
            count = schedule_counts[date_value]

            print(
                f"   • {date_value}: {count}"
            )

            if count != 4:
                validation_ok = False

        # ====================================================
        # PER-DAY FORECAST COUNT
        # ====================================================

        forecast_distribution = (
            db.query(
                GoodsForecast.forecast_date
            )
            .all()
        )

        forecast_counts = {}

        for row in forecast_distribution:
            date_value = row[0]
            forecast_counts[date_value] = (
                forecast_counts.get(
                    date_value,
                    0
                ) + 1
            )

        print(
            "\n📊 Forecast rows per day:"
        )

        for date_value in sorted(
            forecast_counts
        ):
            count = forecast_counts[date_value]

            print(
                f"   • {date_value}: {count}"
            )

            if count != 4:
                validation_ok = False

        # ====================================================
        # FINAL COMMIT
        # ====================================================

        if not validation_ok:
            raise RuntimeError(
                "Final database validation failed."
            )

        db.commit()

        print(
            "\n"
            "============================================================\n"
            "🎉 FINAL DATABASE SEED SUCCESSFUL\n"
            "============================================================\n"
        )

        print(
            "Railway planner source data is now synchronized.\n"
        )

        print(
            "Final state:\n"
            "  Departments       : 3\n"
            "  Stations          : 5\n"
            "  Sections          : 4\n"
            "  Assets            : 6\n"
            "  Maintenance Tasks : 6\n"
            "  Defects           : 3\n"
            "  Trains            : 3\n"
            "  Train Schedules   : 28\n"
            "  Goods Forecasts   : 28\n"
        )

        print(
            f"Planning horizon   : "
            f"{EXPECTED_START_DATE} → "
            f"{EXPECTED_END_DATE}\n"
        )

        print(
            "✅ Database transaction committed successfully.\n"
        )

    except Exception as error:

        db.rollback()

        print(
            "\n❌ DATABASE SEED FAILED"
        )

        print(
            f"Error: {error}\n"
        )

        print(
            "🔄 Database transaction rolled back."
        )

        raise

    finally:

        db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    seed_data()