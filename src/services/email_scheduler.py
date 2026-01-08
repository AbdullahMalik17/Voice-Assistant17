"""
Email Scheduler Service
Schedules emails to be sent at specific times using Google Calendar as the scheduling backend.
"""

import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
from threading import Thread, Event
import logging

from .calendar_service import GoogleCalendarService, CalendarEvent
from .gmail_api import GmailAPIService
from ..utils.logger import EventLogger, MetricsLogger


logger = logging.getLogger(__name__)


@dataclass
class ScheduledEmail:
    """Scheduled email data"""
    id: str
    recipient: str
    subject: str
    body: str
    body_type: str
    scheduled_time: datetime
    calendar_event_id: Optional[str]
    status: str  # pending, sent, failed, cancelled
    created_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "body_type": self.body_type,
            "scheduled_time": self.scheduled_time.isoformat(),
            "calendar_event_id": self.calendar_event_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "error_message": self.error_message
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ScheduledEmail':
        return ScheduledEmail(
            id=data["id"],
            recipient=data["recipient"],
            subject=data["subject"],
            body=data["body"],
            body_type=data["body_type"],
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            calendar_event_id=data.get("calendar_event_id"),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            sent_at=datetime.fromisoformat(data["sent_at"]) if data.get("sent_at") else None,
            error_message=data.get("error_message")
        )


class EmailSchedulerService:
    """
    Email scheduler service that uses Google Calendar for scheduling.

    Features:
    - Schedule emails to be sent at specific times
    - Uses Google Calendar events as scheduling backend
    - Background worker to process scheduled emails
    - Retry logic for failed sends
    - Persistent storage for scheduled emails
    """

    # Special calendar for scheduled emails
    SCHEDULER_CALENDAR_NAME = "Email Scheduler"

    # Check interval for scheduled emails (seconds)
    CHECK_INTERVAL = 60  # 1 minute

    # Prefix for calendar event summaries
    EVENT_PREFIX = "[Scheduled Email]"

    def __init__(
        self,
        calendar_service: GoogleCalendarService,
        gmail_service: GmailAPIService,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        storage_path: str,
        max_retries: int = 3,
        auto_start_worker: bool = False
    ):
        """
        Initialize email scheduler service.

        Args:
            calendar_service: Google Calendar service
            gmail_service: Gmail API service
            logger: Event logger
            metrics_logger: Metrics logger
            storage_path: Path to store scheduled email data
            max_retries: Maximum retry attempts for failed sends
            auto_start_worker: Start background worker automatically
        """
        self.calendar_service = calendar_service
        self.gmail_service = gmail_service
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.storage_path = Path(storage_path)
        self.max_retries = max_retries

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Background worker control
        self.worker_thread: Optional[Thread] = None
        self.worker_stop_event = Event()

        # Load scheduled emails from storage
        self.scheduled_emails: Dict[str, ScheduledEmail] = {}
        self._load_scheduled_emails()

        if auto_start_worker:
            self.start_worker()

        self.logger.info(
            event='EMAIL_SCHEDULER_INITIALIZED',
            message='Email scheduler service initialized',
            storage_path=str(self.storage_path)
        )

    def schedule_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
        body_type: str = 'plain',
        add_to_calendar: bool = True
    ) -> Optional[ScheduledEmail]:
        """
        Schedule an email to be sent at a specific time.

        Args:
            recipient: Recipient email address
            subject: Email subject
            body: Email body
            scheduled_time: When to send the email
            body_type: 'plain' or 'html'
            add_to_calendar: Create a calendar event as reminder

        Returns:
            ScheduledEmail object or None if failed
        """
        try:
            # Generate unique ID
            email_id = f"email_{int(datetime.utcnow().timestamp() * 1000)}"

            # Create calendar event if requested
            calendar_event_id = None
            if add_to_calendar:
                event_summary = f"{self.EVENT_PREFIX} {subject}"
                event_description = self._create_event_description(
                    recipient, subject, body, body_type
                )

                # Create 5-minute event slot
                event_end = scheduled_time + timedelta(minutes=5)

                calendar_event = self.calendar_service.create_event(
                    summary=event_summary,
                    start=scheduled_time,
                    end=event_end,
                    description=event_description,
                    reminder_minutes=10
                )

                if calendar_event:
                    calendar_event_id = calendar_event.id
                    self.logger.info(
                        event='CALENDAR_EVENT_CREATED',
                        message=f'Created calendar event for scheduled email',
                        event_id=calendar_event_id
                    )

            # Create scheduled email object
            scheduled_email = ScheduledEmail(
                id=email_id,
                recipient=recipient,
                subject=subject,
                body=body,
                body_type=body_type,
                scheduled_time=scheduled_time,
                calendar_event_id=calendar_event_id,
                status='pending',
                created_at=datetime.utcnow()
            )

            # Store in memory and persist
            self.scheduled_emails[email_id] = scheduled_email
            self._save_scheduled_email(scheduled_email)

            self.logger.info(
                event='EMAIL_SCHEDULED',
                message=f'Email scheduled for {recipient} at {scheduled_time}',
                email_id=email_id,
                recipient=recipient,
                scheduled_time=scheduled_time.isoformat()
            )

            self.metrics_logger.record_metric('emails_scheduled', 1)

            return scheduled_email

        except Exception as e:
            self.logger.error(
                event='EMAIL_SCHEDULE_ERROR',
                message=f'Failed to schedule email: {str(e)}',
                error=str(e)
            )
            return None

    def cancel_scheduled_email(self, email_id: str) -> bool:
        """
        Cancel a scheduled email.

        Args:
            email_id: Scheduled email ID

        Returns:
            True if cancelled successfully
        """
        try:
            if email_id not in self.scheduled_emails:
                self.logger.warning(
                    event='EMAIL_NOT_FOUND',
                    message=f'Scheduled email not found: {email_id}',
                    email_id=email_id
                )
                return False

            scheduled_email = self.scheduled_emails[email_id]

            # Delete calendar event if exists
            if scheduled_email.calendar_event_id:
                self.calendar_service.delete_event(scheduled_email.calendar_event_id)

            # Update status
            scheduled_email.status = 'cancelled'
            self._save_scheduled_email(scheduled_email)

            self.logger.info(
                event='EMAIL_CANCELLED',
                message=f'Cancelled scheduled email: {email_id}',
                email_id=email_id
            )

            return True

        except Exception as e:
            self.logger.error(
                event='EMAIL_CANCEL_ERROR',
                message=f'Failed to cancel scheduled email: {str(e)}',
                email_id=email_id,
                error=str(e)
            )
            return False

    def list_scheduled_emails(
        self,
        status: Optional[str] = None,
        include_past: bool = False
    ) -> List[ScheduledEmail]:
        """
        List scheduled emails.

        Args:
            status: Filter by status (pending, sent, failed, cancelled)
            include_past: Include emails scheduled in the past

        Returns:
            List of scheduled emails
        """
        emails = list(self.scheduled_emails.values())

        # Filter by status
        if status:
            emails = [e for e in emails if e.status == status]

        # Filter by time
        if not include_past:
            now = datetime.utcnow()
            emails = [e for e in emails if e.scheduled_time > now or e.status != 'pending']

        # Sort by scheduled time
        emails.sort(key=lambda e: e.scheduled_time)

        return emails

    def process_scheduled_emails(self) -> None:
        """
        Process scheduled emails that are due to be sent.
        This should be called periodically by the background worker.
        """
        try:
            now = datetime.utcnow()

            # Find emails due to be sent
            due_emails = [
                email for email in self.scheduled_emails.values()
                if email.status == 'pending' and email.scheduled_time <= now
            ]

            if not due_emails:
                return

            self.logger.info(
                event='PROCESSING_SCHEDULED_EMAILS',
                message=f'Processing {len(due_emails)} scheduled emails',
                count=len(due_emails)
            )

            for email in due_emails:
                self._send_scheduled_email(email)

        except Exception as e:
            self.logger.error(
                event='PROCESS_EMAILS_ERROR',
                message=f'Error processing scheduled emails: {str(e)}',
                error=str(e)
            )

    def _send_scheduled_email(self, scheduled_email: ScheduledEmail) -> None:
        """Send a scheduled email with retry logic"""
        for attempt in range(self.max_retries):
            try:
                # Send email via Gmail API
                result = self.gmail_service.send_email(
                    to=scheduled_email.recipient,
                    subject=scheduled_email.subject,
                    body=scheduled_email.body,
                    body_type=scheduled_email.body_type
                )

                if result.get('success'):
                    # Update status
                    scheduled_email.status = 'sent'
                    scheduled_email.sent_at = datetime.utcnow()
                    scheduled_email.error_message = None
                    self._save_scheduled_email(scheduled_email)

                    # Delete calendar event if exists
                    if scheduled_email.calendar_event_id:
                        self.calendar_service.delete_event(scheduled_email.calendar_event_id)

                    self.logger.info(
                        event='SCHEDULED_EMAIL_SENT',
                        message=f'Sent scheduled email to {scheduled_email.recipient}',
                        email_id=scheduled_email.id,
                        recipient=scheduled_email.recipient
                    )

                    self.metrics_logger.record_metric('scheduled_emails_sent', 1)
                    return

                else:
                    # Email send failed
                    error_msg = result.get('error', 'Unknown error')
                    self.logger.warning(
                        event='EMAIL_SEND_FAILED',
                        message=f'Failed to send scheduled email, attempt {attempt + 1}: {error_msg}',
                        email_id=scheduled_email.id,
                        attempt=attempt + 1,
                        error=error_msg
                    )

                    if attempt < self.max_retries - 1:
                        # Wait before retry with exponential backoff
                        wait_time = (2 ** attempt) * 1.0
                        time.sleep(wait_time)
                    else:
                        # Max retries reached
                        scheduled_email.status = 'failed'
                        scheduled_email.error_message = error_msg
                        self._save_scheduled_email(scheduled_email)

                        self.logger.error(
                            event='SCHEDULED_EMAIL_FAILED',
                            message=f'Scheduled email failed after {self.max_retries} attempts',
                            email_id=scheduled_email.id,
                            recipient=scheduled_email.recipient,
                            error=error_msg
                        )

                        self.metrics_logger.record_metric('scheduled_emails_failed', 1)

            except Exception as e:
                self.logger.error(
                    event='SEND_EMAIL_EXCEPTION',
                    message=f'Exception sending scheduled email: {str(e)}',
                    email_id=scheduled_email.id,
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt >= self.max_retries - 1:
                    scheduled_email.status = 'failed'
                    scheduled_email.error_message = str(e)
                    self._save_scheduled_email(scheduled_email)

    def start_worker(self) -> bool:
        """
        Start background worker to process scheduled emails.

        Returns:
            True if started successfully
        """
        if self.worker_thread and self.worker_thread.is_alive():
            self.logger.warning(
                event='WORKER_ALREADY_RUNNING',
                message='Background worker already running'
            )
            return False

        self.worker_stop_event.clear()
        self.worker_thread = Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self.logger.info(
            event='WORKER_STARTED',
            message='Background worker started'
        )

        return True

    def stop_worker(self) -> bool:
        """
        Stop background worker.

        Returns:
            True if stopped successfully
        """
        if not self.worker_thread or not self.worker_thread.is_alive():
            return False

        self.worker_stop_event.set()
        self.worker_thread.join(timeout=5)

        self.logger.info(
            event='WORKER_STOPPED',
            message='Background worker stopped'
        )

        return True

    def _worker_loop(self) -> None:
        """Background worker loop"""
        self.logger.info(
            event='WORKER_LOOP_STARTED',
            message='Background worker loop started'
        )

        while not self.worker_stop_event.is_set():
            try:
                self.process_scheduled_emails()
            except Exception as e:
                self.logger.error(
                    event='WORKER_LOOP_ERROR',
                    message=f'Error in worker loop: {str(e)}',
                    error=str(e)
                )

            # Wait before next check
            self.worker_stop_event.wait(self.CHECK_INTERVAL)

        self.logger.info(
            event='WORKER_LOOP_STOPPED',
            message='Background worker loop stopped'
        )

    def _create_event_description(
        self,
        recipient: str,
        subject: str,
        body: str,
        body_type: str
    ) -> str:
        """Create calendar event description with email details"""
        return (
            f"Scheduled email to: {recipient}\n"
            f"Subject: {subject}\n"
            f"Body type: {body_type}\n"
            f"\n---\n\n"
            f"{body[:500]}{'...' if len(body) > 500 else ''}"
        )

    def _load_scheduled_emails(self) -> None:
        """Load scheduled emails from storage"""
        try:
            storage_file = self.storage_path / "scheduled_emails.json"
            if not storage_file.exists():
                return

            with open(storage_file, 'r') as f:
                data = json.load(f)

            for email_data in data.get('emails', []):
                email = ScheduledEmail.from_dict(email_data)
                self.scheduled_emails[email.id] = email

            self.logger.info(
                event='EMAILS_LOADED',
                message=f'Loaded {len(self.scheduled_emails)} scheduled emails',
                count=len(self.scheduled_emails)
            )

        except Exception as e:
            self.logger.error(
                event='LOAD_EMAILS_ERROR',
                message=f'Failed to load scheduled emails: {str(e)}',
                error=str(e)
            )

    def _save_scheduled_email(self, email: ScheduledEmail) -> None:
        """Save scheduled email to storage"""
        try:
            storage_file = self.storage_path / "scheduled_emails.json"

            # Load existing data
            if storage_file.exists():
                with open(storage_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {'emails': []}

            # Update or add email
            emails = [e for e in data['emails'] if e['id'] != email.id]
            emails.append(email.to_dict())
            data['emails'] = emails

            # Save
            with open(storage_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(
                event='SAVE_EMAIL_ERROR',
                message=f'Failed to save scheduled email: {str(e)}',
                email_id=email.id,
                error=str(e)
            )


def create_email_scheduler_service(
    calendar_service: GoogleCalendarService,
    gmail_service: GmailAPIService,
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    storage_path: str = "data/scheduled_emails"
) -> EmailSchedulerService:
    """Factory function to create EmailSchedulerService"""
    return EmailSchedulerService(
        calendar_service=calendar_service,
        gmail_service=gmail_service,
        logger=logger,
        metrics_logger=metrics_logger,
        storage_path=storage_path
    )
