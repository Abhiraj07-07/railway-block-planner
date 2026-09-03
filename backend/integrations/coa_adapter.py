from sqlalchemy.orm import Session

from backend.database.models import (
    Block,
    Section,
    TrainSchedule,
)

from .base import BaseRailwayAdapter


class COAAdapter(BaseRailwayAdapter):
    system_name = "COA"

    def fetch(self, db: Session) -> dict:
        schedules = (
            db.query(TrainSchedule)
            .order_by(
                TrainSchedule.schedule_date,
                TrainSchedule.departure_time,
            )
            .all()
        )

        sections = (
            db.query(Section)
            .order_by(Section.section_id)
            .all()
        )

        blocks = (
            db.query(Block)
            .filter(
                Block.status != "CANCELLED"
            )
            .order_by(
                Block.block_date,
                Block.start_time,
            )
            .all()
        )

        return {
            "source_system": "COA",
            "status": "CONNECTED",
            "schedules": schedules,
            "sections": sections,
            "blocks": blocks,
        }

    def normalize(self, data: dict) -> dict:
        train_movements = []

        for schedule in data.get("schedules", []):
            train_movements.append({
                "schedule_id": schedule.schedule_id,
                "train_id": schedule.train_id,
                "section_id": schedule.section_id,
                "date": schedule.schedule_date,
                "arrival_time": schedule.arrival_time,
                "departure_time": schedule.departure_time,
            })

        corridors = []

        for section in data.get("sections", []):
            active_blocks = [
                block
                for block in data.get("blocks", [])
                if block.section_id == section.section_id
            ]

            corridors.append({
                "section_id": section.section_id,
                "section_code": section.section_code,
                "status": section.status,
                "active_blocks": len(active_blocks),
            })

        return {
            "source_system": "COA",
            "status": data.get("status"),
            "train_movements": train_movements,
            "corridor_status": corridors,
        }