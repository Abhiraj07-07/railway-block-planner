from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class BaseRailwayAdapter(ABC):
    """
    Common interface for all railway source systems.
    """

    system_name: str = "UNKNOWN"

    @abstractmethod
    def fetch(self, db: Session) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_data(self, db: Session) -> dict[str, Any]:
        raw_data = self.fetch(db)
        return self.normalize(raw_data)