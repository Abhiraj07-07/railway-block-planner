from datetime import datetime

from sqlalchemy.orm import Session

from .coa_adapter import COAAdapter
from .smms_adapter import SMMSAdapter
from .tdms_adapter import TDMSAdapter
from .tms_adapter import TMSAdapter


class RailwayIntegrationService:

    def __init__(self):
        self.tms = TMSAdapter()
        self.smms = SMMSAdapter()
        self.tdms = TDMSAdapter()
        self.coa = COAAdapter()

    def get_health_status(
        self,
        db: Session,
    ) -> dict:

        adapters = [
            self.tms,
            self.smms,
            self.tdms,
            self.coa,
        ]

        systems = []

        for adapter in adapters:
            try:
                data = adapter.fetch(db)

                systems.append({
                    "system": adapter.system_name,
                    "status": data.get(
                        "status",
                        "UNKNOWN",
                    ),
                    "connected": (
                        data.get("status")
                        == "CONNECTED"
                    ),
                })

            except Exception as exc:
                systems.append({
                    "system": adapter.system_name,
                    "status": "ERROR",
                    "connected": False,
                    "error": str(exc),
                })

        return {
            "integration_layer": "ACTIVE",
            "mode": "DATABASE_BACKED_SIMULATION",
            "systems": systems,
            "checked_at": datetime.utcnow(),
        }

    def get_unified_snapshot(
        self,
        db: Session,
    ) -> dict:

        tms = self.tms.get_data(db)
        smms = self.smms.get_data(db)
        tdms = self.tdms.get_data(db)
        coa = self.coa.get_data(db)

        maintenance_tasks = (
            tms.get("maintenance_tasks", [])
            + smms.get("maintenance_tasks", [])
            + tdms.get("maintenance_tasks", [])
        )

        return {
            "generated_at": datetime.utcnow(),

            "sources": {
                "TMS": {
                    "status": tms.get("status"),
                    "task_count": len(
                        tms.get(
                            "maintenance_tasks",
                            [],
                        )
                    ),
                },
                "SMMS": {
                    "status": smms.get("status"),
                    "task_count": len(
                        smms.get(
                            "maintenance_tasks",
                            [],
                        )
                    ),
                },
                "TDMS": {
                    "status": tdms.get("status"),
                    "task_count": len(
                        tdms.get(
                            "maintenance_tasks",
                            [],
                        )
                    ),
                },
                "COA": {
                    "status": coa.get("status"),
                    "train_movement_count": len(
                        coa.get(
                            "train_movements",
                            [],
                        )
                    ),
                    "corridor_count": len(
                        coa.get(
                            "corridor_status",
                            [],
                        )
                    ),
                },
            },

            "unified_data": {
                "maintenance_tasks": maintenance_tasks,
                "train_movements": coa.get(
                    "train_movements",
                    [],
                ),
                "corridor_status": coa.get(
                    "corridor_status",
                    [],
                ),
            },
        }


integration_service = RailwayIntegrationService()