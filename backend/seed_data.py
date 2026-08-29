from pathlib import Path

import pandas as pd
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
# HELPER
# ============================================================

def normalize_section_code(value) -> str:
    """
    Converts:
        1       -> SEC01
        2       -> SEC02
        SEC01   -> SEC01
    """
    section_code = str(value).strip()

    if section_code.upper().startswith("SEC"):
        return section_code.upper()

    return f"SEC{int(float(section_code)):02d}"


# ============================================================
# MAIN SEED FUNCTION
# ============================================================

def seed_data():

    db: Session = SessionLocal()

    try:
        print("\n🚆 Starting Railway Block Planner data import...\n")

        # ====================================================
        # 1. DEPARTMENTS
        # ====================================================

        departments = [
            Department(
                department_code="ENG",
                department_name="Engineering"
            ),
            Department(
                department_code="TRD",
                department_name="Traction Distribution"
            ),
            Department(
                department_code="SNT",
                department_name="Signal & Telecommunication"
            ),
        ]

        db.add_all(departments)
        db.commit()

        print("✅ Departments inserted")


        # ====================================================
        # 2. STATIONS
        # ====================================================

        stations_df = pd.read_csv(
            DATA_DIR / "stations.csv"
        )

        station_objects = []

        for _, row in stations_df.iterrows():

            station_objects.append(
                Station(
                    station_code=str(row["station_code"]).strip(),
                    station_name=str(row["station_name"]).strip()
                )
            )

        db.add_all(station_objects)
        db.commit()

        print(
            f"✅ Stations inserted: "
            f"{len(station_objects)}"
        )


        # ====================================================
        # 3. SECTIONS
        # ====================================================

        sections_df = pd.read_csv(
            DATA_DIR / "sections.csv"
        )

        station_map = {
            station.station_code: station.station_id
            for station in db.query(Station).all()
        }

        section_objects = []

        for _, row in sections_df.iterrows():

            from_code = str(
                row["from_station"]
            ).strip()

            to_code = str(
                row["to_station"]
            ).strip()

            if from_code not in station_map:
                raise ValueError(
                    f"Unknown from_station: {from_code}"
                )

            if to_code not in station_map:
                raise ValueError(
                    f"Unknown to_station: {to_code}"
                )

            section_objects.append(
                Section(
                    section_code=str(
                        row["section_code"]
                    ).strip(),

                    from_station_id=station_map[
                        from_code
                    ],

                    to_station_id=station_map[
                        to_code
                    ],

                    distance_km=float(
                        row["distance_km"]
                    ),

                    status="ACTIVE"
                )
            )

        db.add_all(section_objects)
        db.commit()

        print(
            f"✅ Sections inserted: "
            f"{len(section_objects)}"
        )


        # ====================================================
        # 4. ASSETS
        # ====================================================

        assets_df = pd.read_csv(
            DATA_DIR / "assets.csv"
        )

        department_map = {
            department.department_code:
                department.department_id

            for department
            in db.query(Department).all()
        }

        section_map = {
            section.section_code:
                section.section_id

            for section
            in db.query(Section).all()
        }

        department_lookup = {
            "Engineering": "ENG",
            "Traction": "TRD",
            "Traction Distribution": "TRD",
            "S&T": "SNT",
            "Signal & Telecommunication": "SNT",
        }

        asset_objects = []

        for _, row in assets_df.iterrows():

            department_name = str(
                row["department"]
            ).strip()

            department_code = department_lookup.get(
                department_name,
                department_name
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
                    asset_code=str(
                        row["asset_code"]
                    ).strip(),

                    asset_type=str(
                        row["asset_type"]
                    ).strip().upper(),

                    section_id=section_map[
                        section_code
                    ],

                    department_id=department_map[
                        department_code
                    ],

                    criticality=str(
                        row["criticality"]
                    ).strip().upper(),

                    status=str(
                        row.get(
                            "status",
                            "ACTIVE"
                        )
                    ).strip().upper()
                )
            )

        db.add_all(asset_objects)
        db.commit()

        print(
            f"✅ Assets inserted: "
            f"{len(asset_objects)}"
        )


        # ====================================================
        # 5. MAINTENANCE TASKS
        # ====================================================

        maintenance_files = [
            ("tms_tasks.csv", "TMS"),
            ("smms_tasks.csv", "SMMS"),
            ("tdms_tasks.csv", "TDMS"),
        ]

        asset_map = {
            asset.asset_code:
                asset.asset_id

            for asset
            in db.query(Asset).all()
        }

        maintenance_objects = []

        source_department_map = {
            "TMS": "ENG",
            "SMMS": "SNT",
            "TDMS": "TRD",
        }

        for filename, source_system in maintenance_files:

            file_path = DATA_DIR / filename

            df = pd.read_csv(file_path)

            department_code = (
                source_department_map[
                    source_system
                ]
            )

            for _, row in df.iterrows():

                asset_code = str(
                    row["asset_code"]
                ).strip()

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
                        task_code=str(
                            row["task_id"]
                        ).strip(),

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

                        task_type=str(
                            row["task_type"]
                        ).strip(),

                        severity=str(
                            row["severity"]
                        ).strip().upper(),

                        duration_hours=float(
                            row["duration_hours"]
                        ),

                        status=str(
                            row["status"]
                        ).strip().upper(),

                        due_date=pd.to_datetime(
                            row["due_date"]
                        ).date(),

                        description=(
                            f"{row['task_type']} "
                            f"imported from "
                            f"{source_system}"
                        )

                        # created_at intentionally omitted.
                        # Database generates it automatically.
                    )
                )

        db.add_all(maintenance_objects)
        db.commit()

        print(
            f"✅ Maintenance tasks inserted: "
            f"{len(maintenance_objects)}"
        )


        # ====================================================
        # 6. DEFECTS
        # ====================================================

        defects_df = pd.read_csv(
            DATA_DIR / "defects.csv"
        )

        defect_objects = []

        for _, row in defects_df.iterrows():

            asset_code = str(
                row["asset_code"]
            ).strip()

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
                    defect_code=str(
                        row["defect_id"]
                    ).strip(),

                    asset_id=asset_map[
                        asset_code
                    ],

                    section_id=section_map[
                        section_code
                    ],

                    severity=str(
                        row["severity"]
                    ).strip().upper(),

                    description=str(
                        row["description"]
                    ).strip(),

                    detected_date=pd.to_datetime(
                        row["detected_date"]
                    ).date(),

                    status=str(
                        row["status"]
                    ).strip().upper()
                )
            )

        db.add_all(defect_objects)
        db.commit()

        print(
            f"✅ Defects inserted: "
            f"{len(defect_objects)}"
        )


        # ====================================================
        # 7. TRAINS
        # ====================================================

        trains_df = pd.read_csv(
            DATA_DIR / "trains.csv"
        )

        train_objects = []

        for _, row in trains_df.iterrows():

            train_objects.append(
                Train(
                    train_no=str(
                        row["train_no"]
                    ).strip(),

                    train_name=str(
                        row["train_name"]
                    ).strip(),

                    train_type=str(
                        row["train_type"]
                    ).strip().upper(),

                    priority=str(
                        row["priority"]
                    ).strip().upper()
                )
            )

        db.add_all(train_objects)
        db.commit()

        print(
            f"✅ Trains inserted: "
            f"{len(train_objects)}"
        )


        # ====================================================
        # 8. TRAIN SCHEDULE
        # ====================================================

        schedule_df = pd.read_csv(
            DATA_DIR / "train_schedule.csv"
        )

        train_objects_db = db.query(
            Train
        ).all()

        train_by_id = {
            str(train.train_id): train
            for train in train_objects_db
        }

        train_by_no = {
            train.train_no: train
            for train in train_objects_db
        }

        schedule_objects = []

        for _, row in schedule_df.iterrows():

            train_identifier = str(
                row["train_id"]
            ).strip()

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

            schedule_objects.append(
                TrainSchedule(
                    train_id=matching_train.train_id,

                    section_id=section_map[
                        section_code
                    ],

                    schedule_date=pd.to_datetime(
                        row["date"]
                    ).date(),

                    arrival_time=pd.to_datetime(
                        row["arrival_time"]
                    ).time(),

                    departure_time=pd.to_datetime(
                        row["departure_time"]
                    ).time()
                )
            )

        db.add_all(schedule_objects)
        db.commit()

        print(
            f"✅ Train schedules inserted: "
            f"{len(schedule_objects)}"
        )


        # ====================================================
        # 9. GOODS TRAIN FORECAST
        # ====================================================

        forecast_df = pd.read_csv(
            DATA_DIR / "goods_forecast.csv"
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

            forecast_objects.append(
                GoodsForecast(
                    section_id=section_map[
                        section_code
                    ],

                    forecast_date=pd.to_datetime(
                        row["date"]
                    ).date(),

                    expected_goods_trains=int(
                        row["expected_goods_trains"]
                    )
                )
            )

        db.add_all(forecast_objects)
        db.commit()

        print(
            f"✅ Goods forecasts inserted: "
            f"{len(forecast_objects)}"
        )


        # ====================================================
        # SUCCESS
        # ====================================================

        print(
            "\n🎉 ALL DATA IMPORTED SUCCESSFULLY!"
        )

        print(
            "🚆 Railway Block Planner "
            "database is ready.\n"
        )


    except Exception as error:

        db.rollback()

        print(
            "\n❌ DATA IMPORT FAILED"
        )

        print(
            f"Error: {error}\n"
        )

        raise

    finally:

        db.close()


# ============================================================
# RUN SCRIPT
# ============================================================

if __name__ == "__main__":
    seed_data()