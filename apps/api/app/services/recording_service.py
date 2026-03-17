from app.core.exceptions import NotFoundError
from app.models.recording import Recording
from app.repos.recording_repo import RecordingRepository
from app.schemas.recording import RecordingCreate, RecordingUpdate


class RecordingService:
    def __init__(self, recording_repo: RecordingRepository) -> None:
        self.recording_repo = recording_repo

    def list_recordings(self) -> list[Recording]:
        return self.recording_repo.list()

    def create_recording(self, payload: RecordingCreate) -> Recording:
        recording = Recording(**payload.model_dump())
        return self.recording_repo.create(recording)

    def get_recording(self, recording_id: str) -> Recording:
        recording = self.recording_repo.get(recording_id)
        if recording is None:
            raise NotFoundError("Recording", recording_id)
        return recording

    def update_recording(self, recording_id: str, payload: RecordingUpdate) -> Recording:
        recording = self.get_recording(recording_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(recording, field, value)
        return self.recording_repo.update(recording)

    def delete_recording(self, recording_id: str) -> None:
        recording = self.get_recording(recording_id)
        self.recording_repo.delete(recording)
