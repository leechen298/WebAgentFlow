from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recording import Recording


class RecordingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Recording]:
        stmt = select(Recording).order_by(Recording.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get(self, recording_id: str) -> Recording | None:
        return self.session.get(Recording, recording_id)

    def create(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.commit()
        self.session.refresh(recording)
        return recording

    def update(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.commit()
        self.session.refresh(recording)
        return recording

    def delete(self, recording: Recording) -> None:
        self.session.delete(recording)
        self.session.commit()
