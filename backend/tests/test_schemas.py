"""
Tests unitarios de schemas y enums.
Cubre: R-MOD-02, R-MOD-03, R-MOD-04, R-CREATE-03..06.
"""
import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class TestTaskCreate:
    def test_valid_with_only_title(self) -> None:
        """Título mínimo → objeto válido con defaults."""
        task = TaskCreate(title="T")
        assert task.title == "T"
        assert task.description is None
        assert task.status == TaskStatus.pending
        assert task.priority == TaskPriority.medium

    def test_empty_title_raises_validation_error(self) -> None:
        """title='' → ValidationError (R-MOD-02)."""
        with pytest.raises(ValidationError):
            TaskCreate(title="")

    def test_missing_title_raises_validation_error(self) -> None:
        """Sin title → ValidationError (R-MOD-02)."""
        with pytest.raises(ValidationError):
            TaskCreate()  # type: ignore[call-arg]

    def test_null_title_raises_validation_error(self) -> None:
        """title=None → ValidationError (R-MOD-02)."""
        with pytest.raises(ValidationError):
            TaskCreate(title=None)  # type: ignore[arg-type]

    def test_invalid_status_raises_validation_error(self) -> None:
        """status inválido → ValidationError (R-MOD-03)."""
        with pytest.raises(ValidationError):
            TaskCreate(title="T", status="invalido")  # type: ignore[arg-type]

    def test_invalid_priority_raises_validation_error(self) -> None:
        """priority inválido → ValidationError (R-MOD-04)."""
        with pytest.raises(ValidationError):
            TaskCreate(title="T", priority="invalido")  # type: ignore[arg-type]


class TestTaskUpdate:
    def test_empty_update_is_valid(self) -> None:
        """TaskUpdate() sin args → objeto válido (todos None/unset)."""
        update = TaskUpdate()
        assert update.title is None
        assert update.status is None
        assert update.priority is None

    def test_empty_title_raises_validation_error(self) -> None:
        """title='' en update → ValidationError (R-UPDATE-03)."""
        with pytest.raises(ValidationError):
            TaskUpdate(title="")

    def test_invalid_status_raises_validation_error(self) -> None:
        """status inválido en update → ValidationError (R-UPDATE-04)."""
        with pytest.raises(ValidationError):
            TaskUpdate(status="invalido")  # type: ignore[arg-type]
