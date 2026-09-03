from sqlalchemy.orm import Session

from backend.database.models import MaintenanceTask

from .base import BaseRailwayAdapter


class SMMSAdapter(BaseRailwayAdapter):
    system_name = "SMMS"

    def fetch(self, db: Session) -> dict:
        tasks = (
            db.query(MaintenanceTask)
            .filter(
                MaintenanceTask.source_system == "SMMS"
            )
            .order_by(MaintenanceTask.task_id)
            .all()
        )

        return {
            "source_system": "SMMS",
            "status": "CONNECTED",
            "tasks": tasks,
        }

    def normalize(self, data: dict) -> dict:
        tasks = []

        for task in data.get("tasks", []):
            tasks.append({
                "source_system": "SMMS",
                "task_id": task.task_id,
                "task_code": task.task_code,
                "department_id": task.department_id,
                "asset_id": task.asset_id,
                "section_id": task.section_id,
                "task_type": task.task_type,
                "severity": task.severity,
                "duration_hours": (
                    float(task.duration_hours)
                    if task.duration_hours is not None
                    else None
                ),
                "status": task.status,
                "due_date": task.due_date,
                "description": task.description,
            })

        return {
            "source_system": "SMMS",
            "status": data.get("status"),
            "maintenance_tasks": tasks,
        }