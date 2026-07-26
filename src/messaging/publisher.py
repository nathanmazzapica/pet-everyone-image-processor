from abc import ABC, abstractmethod

from src.models.status_update import JobStatusUpdate


class Publisher(ABC):
    @abstractmethod
    def publish(self, evt: JobStatusUpdate) -> None:
        pass