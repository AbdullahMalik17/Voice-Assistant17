"""
Tests for Email Scheduler Service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import json

from src.services.email_scheduler import (
    EmailSchedulerService,
    ScheduledEmail,
    create_email_scheduler_service
)
from src.services.calendar_service import CalendarEvent
from src.utils.logger import EventLogger, MetricsLogger


@pytest.fixture
def mock_calendar_service():
    """Mock calendar service"""
    service = Mock()

    # Mock create_event
    mock_event = CalendarEvent(
        id="event_123",
        summary="[Scheduled Email] Test Subject",
        description="Test description",
        location=None,
        start=datetime.utcnow(),
        end=datetime.utcnow() + timedelta(minutes=5),
        attendees=[],
        reminder_minutes=10,
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
        creator_email="test@example.com",
        organizer_email="test@example.com",
        html_link="https://calendar.google.com/event/123"
    )
    service.create_event.return_value = mock_event
    service.delete_event.return_value = True

    return service


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service"""
    service = Mock()

    # Mock send_email - success
    service.send_email.return_value = {
        "success": True,
        "message": "Email sent successfully",
        "message_id": "msg_123"
    }

    return service


@pytest.fixture
def mock_logger():
    """Mock event logger"""
    logger = Mock(spec=EventLogger)
    return logger


@pytest.fixture
def mock_metrics_logger():
    """Mock metrics logger"""
    logger = Mock(spec=MetricsLogger)
    return logger


@pytest.fixture
def temp_storage():
    """Temporary storage directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def email_scheduler(
    mock_calendar_service,
    mock_gmail_service,
    mock_logger,
    mock_metrics_logger,
    temp_storage
):
    """Email scheduler service instance"""
    return EmailSchedulerService(
        calendar_service=mock_calendar_service,
        gmail_service=mock_gmail_service,
        logger=mock_logger,
        metrics_logger=mock_metrics_logger,
        storage_path=temp_storage,
        auto_start_worker=False
    )


class TestEmailScheduler:
    """Test EmailSchedulerService"""

    def test_schedule_email_success(
        self,
        email_scheduler,
        mock_calendar_service,
        mock_metrics_logger
    ):
        """Test scheduling an email successfully"""
        scheduled_time = datetime.utcnow() + timedelta(hours=1)

        result = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=scheduled_time,
            body_type='plain',
            add_to_calendar=True
        )

        # Verify result
        assert result is not None
        assert result.recipient == "test@example.com"
        assert result.subject == "Test Subject"
        assert result.body == "Test body"
        assert result.body_type == 'plain'
        assert result.status == 'pending'
        assert result.calendar_event_id == "event_123"

        # Verify calendar event created
        mock_calendar_service.create_event.assert_called_once()

        # Verify metric recorded
        mock_metrics_logger.record_metric.assert_called_with('emails_scheduled', 1)

        # Verify stored in memory
        assert result.id in email_scheduler.scheduled_emails

    def test_schedule_email_without_calendar(
        self,
        email_scheduler,
        mock_calendar_service
    ):
        """Test scheduling email without calendar event"""
        scheduled_time = datetime.utcnow() + timedelta(hours=1)

        result = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=scheduled_time,
            add_to_calendar=False
        )

        # Verify no calendar event created
        mock_calendar_service.create_event.assert_not_called()

        # Verify email scheduled
        assert result is not None
        assert result.calendar_event_id is None

    def test_cancel_scheduled_email(
        self,
        email_scheduler,
        mock_calendar_service
    ):
        """Test cancelling a scheduled email"""
        # Schedule an email
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        scheduled_email = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=scheduled_time
        )

        # Cancel it
        result = email_scheduler.cancel_scheduled_email(scheduled_email.id)

        # Verify cancelled
        assert result is True
        assert scheduled_email.status == 'cancelled'

        # Verify calendar event deleted
        mock_calendar_service.delete_event.assert_called_once_with("event_123")

    def test_list_scheduled_emails(self, email_scheduler):
        """Test listing scheduled emails"""
        # Schedule multiple emails
        now = datetime.utcnow()

        email1 = email_scheduler.schedule_email(
            recipient="test1@example.com",
            subject="Test 1",
            body="Body 1",
            scheduled_time=now + timedelta(hours=1),
            add_to_calendar=False
        )

        email2 = email_scheduler.schedule_email(
            recipient="test2@example.com",
            subject="Test 2",
            body="Body 2",
            scheduled_time=now + timedelta(hours=2),
            add_to_calendar=False
        )

        # Cancel one
        email_scheduler.cancel_scheduled_email(email2.id)

        # List all
        all_emails = email_scheduler.list_scheduled_emails()
        assert len(all_emails) == 2

        # List pending only
        pending = email_scheduler.list_scheduled_emails(status='pending')
        assert len(pending) == 1
        assert pending[0].id == email1.id

        # List cancelled only
        cancelled = email_scheduler.list_scheduled_emails(status='cancelled')
        assert len(cancelled) == 1
        assert cancelled[0].id == email2.id

    def test_process_scheduled_emails_sends_due_email(
        self,
        email_scheduler,
        mock_gmail_service,
        mock_metrics_logger
    ):
        """Test processing sends emails that are due"""
        # Schedule email in the past
        past_time = datetime.utcnow() - timedelta(minutes=5)

        email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=past_time,
            add_to_calendar=False
        )

        # Process scheduled emails
        email_scheduler.process_scheduled_emails()

        # Verify email sent
        mock_gmail_service.send_email.assert_called_once_with(
            to="test@example.com",
            subject="Test Subject",
            body="Test body",
            body_type='plain'
        )

        # Verify metric recorded
        mock_metrics_logger.record_metric.assert_any_call('scheduled_emails_sent', 1)

    def test_process_scheduled_emails_skips_future_emails(
        self,
        email_scheduler,
        mock_gmail_service
    ):
        """Test processing skips emails scheduled in the future"""
        # Schedule email in the future
        future_time = datetime.utcnow() + timedelta(hours=1)

        email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=future_time,
            add_to_calendar=False
        )

        # Process scheduled emails
        email_scheduler.process_scheduled_emails()

        # Verify email NOT sent
        mock_gmail_service.send_email.assert_not_called()

    def test_send_scheduled_email_with_retry(
        self,
        email_scheduler,
        mock_gmail_service,
        mock_metrics_logger
    ):
        """Test sending scheduled email retries on failure"""
        # Mock initial failures, then success
        mock_gmail_service.send_email.side_effect = [
            {"success": False, "error": "Temporary error"},
            {"success": False, "error": "Temporary error"},
            {"success": True, "message": "Email sent", "message_id": "msg_123"}
        ]

        # Schedule email in the past
        past_time = datetime.utcnow() - timedelta(minutes=5)
        scheduled_email = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=past_time,
            add_to_calendar=False
        )

        # Send with retry
        with patch('time.sleep'):  # Mock sleep to speed up test
            email_scheduler._send_scheduled_email(scheduled_email)

        # Verify retried 3 times
        assert mock_gmail_service.send_email.call_count == 3

        # Verify final status is sent
        assert scheduled_email.status == 'sent'
        assert scheduled_email.sent_at is not None

    def test_send_scheduled_email_fails_after_max_retries(
        self,
        email_scheduler,
        mock_gmail_service,
        mock_metrics_logger
    ):
        """Test sending scheduled email fails after max retries"""
        # Mock all failures
        mock_gmail_service.send_email.return_value = {
            "success": False,
            "error": "Permanent error"
        }

        # Schedule email in the past
        past_time = datetime.utcnow() - timedelta(minutes=5)
        scheduled_email = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=past_time,
            add_to_calendar=False
        )

        # Send with retry
        with patch('time.sleep'):  # Mock sleep to speed up test
            email_scheduler._send_scheduled_email(scheduled_email)

        # Verify retried 3 times
        assert mock_gmail_service.send_email.call_count == 3

        # Verify final status is failed
        assert scheduled_email.status == 'failed'
        assert scheduled_email.error_message == "Permanent error"

        # Verify metric recorded
        mock_metrics_logger.record_metric.assert_any_call('scheduled_emails_failed', 1)

    def test_persistence(self, email_scheduler, temp_storage):
        """Test scheduled emails are persisted to disk"""
        # Schedule email
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        scheduled_email = email_scheduler.schedule_email(
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            scheduled_time=scheduled_time,
            add_to_calendar=False
        )

        # Verify saved to disk
        storage_file = Path(temp_storage) / "scheduled_emails.json"
        assert storage_file.exists()

        with open(storage_file, 'r') as f:
            data = json.load(f)

        assert len(data['emails']) == 1
        assert data['emails'][0]['id'] == scheduled_email.id
        assert data['emails'][0]['recipient'] == "test@example.com"

    def test_load_scheduled_emails(
        self,
        mock_calendar_service,
        mock_gmail_service,
        mock_logger,
        mock_metrics_logger,
        temp_storage
    ):
        """Test loading scheduled emails from disk"""
        # Create test data
        storage_file = Path(temp_storage) / "scheduled_emails.json"
        test_data = {
            "emails": [
                {
                    "id": "email_1",
                    "recipient": "test@example.com",
                    "subject": "Test Subject",
                    "body": "Test body",
                    "body_type": "plain",
                    "scheduled_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    "calendar_event_id": "event_123",
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                    "sent_at": None,
                    "error_message": None
                }
            ]
        }

        with open(storage_file, 'w') as f:
            json.dump(test_data, f)

        # Create service (should load data)
        scheduler = EmailSchedulerService(
            calendar_service=mock_calendar_service,
            gmail_service=mock_gmail_service,
            logger=mock_logger,
            metrics_logger=mock_metrics_logger,
            storage_path=temp_storage,
            auto_start_worker=False
        )

        # Verify loaded
        assert len(scheduler.scheduled_emails) == 1
        assert "email_1" in scheduler.scheduled_emails
        assert scheduler.scheduled_emails["email_1"].recipient == "test@example.com"

    def test_worker_start_stop(self, email_scheduler):
        """Test background worker start and stop"""
        # Start worker
        result = email_scheduler.start_worker()
        assert result is True
        assert email_scheduler.worker_thread is not None
        assert email_scheduler.worker_thread.is_alive()

        # Try to start again (should fail)
        result = email_scheduler.start_worker()
        assert result is False

        # Stop worker
        result = email_scheduler.stop_worker()
        assert result is True
        assert not email_scheduler.worker_thread.is_alive()

    def test_factory_function(
        self,
        mock_calendar_service,
        mock_gmail_service,
        mock_logger,
        mock_metrics_logger
    ):
        """Test factory function creates service correctly"""
        scheduler = create_email_scheduler_service(
            calendar_service=mock_calendar_service,
            gmail_service=mock_gmail_service,
            logger=mock_logger,
            metrics_logger=mock_metrics_logger,
            storage_path="data/test_scheduled_emails"
        )

        assert scheduler is not None
        assert isinstance(scheduler, EmailSchedulerService)


class TestScheduledEmail:
    """Test ScheduledEmail dataclass"""

    def test_to_dict(self):
        """Test converting ScheduledEmail to dict"""
        now = datetime.utcnow()
        email = ScheduledEmail(
            id="email_1",
            recipient="test@example.com",
            subject="Test Subject",
            body="Test body",
            body_type='plain',
            scheduled_time=now,
            calendar_event_id="event_123",
            status='pending',
            created_at=now
        )

        result = email.to_dict()

        assert result['id'] == "email_1"
        assert result['recipient'] == "test@example.com"
        assert result['subject'] == "Test Subject"
        assert result['body'] == "Test body"
        assert result['body_type'] == 'plain'
        assert result['scheduled_time'] == now.isoformat()
        assert result['calendar_event_id'] == "event_123"
        assert result['status'] == 'pending'
        assert result['created_at'] == now.isoformat()

    def test_from_dict(self):
        """Test creating ScheduledEmail from dict"""
        now = datetime.utcnow()
        data = {
            "id": "email_1",
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "body": "Test body",
            "body_type": "plain",
            "scheduled_time": now.isoformat(),
            "calendar_event_id": "event_123",
            "status": "pending",
            "created_at": now.isoformat(),
            "sent_at": None,
            "error_message": None
        }

        email = ScheduledEmail.from_dict(data)

        assert email.id == "email_1"
        assert email.recipient == "test@example.com"
        assert email.subject == "Test Subject"
        assert email.body == "Test body"
        assert email.body_type == "plain"
        assert email.calendar_event_id == "event_123"
        assert email.status == "pending"
        assert email.sent_at is None
