"""
Tests unitarios de schemas y enums.
Cubre: R-MOD-02, R-MOD-03, R-MOD-04, R-CREATE-03..06, due_date validator.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

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


class TestTaskCreateDueDate:
    """Unit tests for due_date validator on TaskCreate (RED-first for T-01)."""

    def _pin_today(self, today: date) -> MagicMock:
        """Return a mock for app.schemas.task.date that pins date.today()."""
        mock_date = MagicMock(spec=date)
        mock_date.today.return_value = today
        # Allow TaskCreate to construct date instances from its own calls.
        mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        return mock_date

    def test_due_date_past_raises(self) -> None:
        """past due_date on TaskCreate → ValidationError (422 path)."""
        today = date(2026, 6, 8)
        yesterday = today - timedelta(days=1)
        with patch("app.schemas.task.date", self._pin_today(today)):
            with pytest.raises(ValidationError):
                TaskCreate(title="T", due_date=yesterday)

    def test_due_date_today_valid(self) -> None:
        """due_date == today on TaskCreate → valid (boundary: today allowed)."""
        today = date(2026, 6, 8)
        with patch("app.schemas.task.date", self._pin_today(today)):
            task = TaskCreate(title="T", due_date=today)
        assert task.due_date == today

    def test_due_date_future_valid(self) -> None:
        """due_date in the future on TaskCreate → valid."""
        today = date(2026, 6, 8)
        tomorrow = today + timedelta(days=1)
        with patch("app.schemas.task.date", self._pin_today(today)):
            task = TaskCreate(title="T", due_date=tomorrow)
        assert task.due_date == tomorrow

    def test_due_date_none_valid(self) -> None:
        """due_date=None on TaskCreate → valid (optional field)."""
        task = TaskCreate(title="T", due_date=None)
        assert task.due_date is None

    def test_due_date_omitted_defaults_to_none(self) -> None:
        """due_date omitted on TaskCreate → None (back-compat)."""
        task = TaskCreate(title="T")
        assert task.due_date is None

    def test_taskupdate_past_date_valid(self) -> None:
        """past due_date on TaskUpdate → valid (no restriction on update)."""
        yesterday = date(2026, 6, 7)
        update = TaskUpdate(due_date=yesterday)
        assert update.due_date == yesterday
