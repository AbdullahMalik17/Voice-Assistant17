"""
Google Calendar Service
Provides calendar management using Google Calendar API.
"""

import os
import pickle
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..utils.logger import EventLogger, MetricsLogger


SCOPES = ['https://www.googleapis.com/auth/calendar']


@dataclass
class CalendarEvent:
    """Calendar event data"""
    id: str
    summary: str
    description: Optional[str]
    location: Optional[str]
    start: datetime
    end: datetime
    attendees: List[str]
    reminder_minutes: Optional[int]
    created: datetime
    updated: datetime
    creator_email: str
    organizer_email: str
    html_link: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "attendees": self.attendees,
            "reminder_minutes": self.reminder_minutes,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "creator_email": self.creator_email,
            "organizer_email": self.organizer_email,
            "html_link": self.html_link
        }


class GoogleCalendarService:
    """
    Google Calendar service for calendar management.

    Features:
    - List events
    - Create events
    - Update events
    - Delete events
    - Search events
    - Quick add (natural language)
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        credentials_path: str,
        token_path: str,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        max_retries: int = 3
    ):
        """
        Initialize Google Calendar service.

        Args:
            credentials_path: Path to OAuth2 credentials JSON
            token_path: Path to store token pickle file
            logger: Event logger
            metrics_logger: Metrics logger
            max_retries: Maximum retry attempts
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.max_retries = max_retries

        self.service = None
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize Google Calendar API service with OAuth2"""
        try:
            creds = None

            # Load existing token
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)

            # Refresh or create new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path,
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)

            self.service = build('calendar', 'v3', credentials=creds)

            self.logger.info(
                event='CALENDAR_SERVICE_INITIALIZED',
                message='Google Calendar service initialized successfully'
            )

        except Exception as e:
            self.logger.error(
                event='CALENDAR_INIT_ERROR',
                message=f'Failed to initialize Calendar service: {str(e)}',
                error=str(e)
            )
            self.service = None

    def list_events(
        self,
        max_results: int = 10,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None
    ) -> Optional[List[CalendarEvent]]:
        """
        List calendar events.

        Args:
            max_results: Maximum number of events to return
            calendar_id: Calendar identifier (default: 'primary')
            time_min: Minimum start time (default: now)
            time_max: Maximum start time

        Returns:
            List of CalendarEvent or None if failed
        """
        if not self.service:
            self.logger.error(
                event='CALENDAR_SERVICE_NOT_INITIALIZED',
                message='Calendar service not initialized'
            )
            return None

        try:
            # Default to current time
            if not time_min:
                time_min = datetime.utcnow()

            time_min_str = time_min.isoformat() + 'Z'
            time_max_str = None
            if time_max:
                time_max_str = time_max.isoformat() + 'Z'

            request_params = {
                'calendarId': calendar_id,
                'timeMin': time_min_str,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }

            if time_max_str:
                request_params['timeMax'] = time_max_str

            events_result = self._execute_with_retry(
                lambda: self.service.events().list(**request_params).execute()
            )

            if not events_result:
                return None

            events = events_result.get('items', [])
            return [self._parse_event(event) for event in events]

        except Exception as e:
            self.logger.error(
                event='CALENDAR_LIST_ERROR',
                message=f'Failed to list events: {str(e)}',
                error=str(e)
            )
            return None

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminder_minutes: int = 10,
        calendar_id: str = 'primary'
    ) -> Optional[CalendarEvent]:
        """
        Create a calendar event.

        Args:
            summary: Event title
            start: Start datetime
            end: End datetime
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            reminder_minutes: Reminder before event (minutes)
            calendar_id: Calendar identifier

        Returns:
            Created CalendarEvent or None if failed
        """
        if not self.service:
            return None

        try:
            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': reminder_minutes},
                    ],
                },
            }

            if description:
                event_body['description'] = description

            if location:
                event_body['location'] = location

            if attendees:
                event_body['attendees'] = [
                    {'email': email} for email in attendees
                ]

            created_event = self._execute_with_retry(
                lambda: self.service.events().insert(
                    calendarId=calendar_id,
                    body=event_body
                ).execute()
            )

            if created_event:
                self.logger.info(
                    event='CALENDAR_EVENT_CREATED',
                    message=f'Created event: {summary}',
                    event_id=created_event.get('id')
                )
                return self._parse_event(created_event)

            return None

        except Exception as e:
            self.logger.error(
                event='CALENDAR_CREATE_ERROR',
                message=f'Failed to create event: {str(e)}',
                summary=summary,
                error=str(e)
            )
            return None

    def quick_add(
        self,
        text: str,
        calendar_id: str = 'primary'
    ) -> Optional[CalendarEvent]:
        """
        Create event using natural language.

        Examples:
        - "Meeting tomorrow at 3pm"
        - "Lunch with John on Friday at noon"
        - "Team standup every weekday at 9am"

        Args:
            text: Natural language event description
            calendar_id: Calendar identifier

        Returns:
            Created CalendarEvent or None if failed
        """
        if not self.service:
            return None

        try:
            created_event = self._execute_with_retry(
                lambda: self.service.events().quickAdd(
                    calendarId=calendar_id,
                    text=text
                ).execute()
            )

            if created_event:
                self.logger.info(
                    event='CALENDAR_QUICK_ADD',
                    message=f'Quick added event: {text}',
                    event_id=created_event.get('id')
                )
                return self._parse_event(created_event)

            return None

        except Exception as e:
            self.logger.error(
                event='CALENDAR_QUICK_ADD_ERROR',
                message=f'Failed to quick add event: {str(e)}',
                text=text,
                error=str(e)
            )
            return None

    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = 'primary'
    ) -> Optional[CalendarEvent]:
        """
        Update an existing event.

        Args:
            event_id: Event ID to update
            summary: New title (if provided)
            start: New start time (if provided)
            end: New end time (if provided)
            description: New description (if provided)
            location: New location (if provided)
            calendar_id: Calendar identifier

        Returns:
            Updated CalendarEvent or None if failed
        """
        if not self.service:
            return None

        try:
            # Get existing event
            event = self._execute_with_retry(
                lambda: self.service.events().get(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
            )

            if not event:
                return None

            # Update fields
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start:
                event['start'] = {
                    'dateTime': start.isoformat(),
                    'timeZone': 'UTC'
                }
            if end:
                event['end'] = {
                    'dateTime': end.isoformat(),
                    'timeZone': 'UTC'
                }

            updated_event = self._execute_with_retry(
                lambda: self.service.events().update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event
                ).execute()
            )

            if updated_event:
                self.logger.info(
                    event='CALENDAR_EVENT_UPDATED',
                    message=f'Updated event: {event_id}',
                    event_id=event_id
                )
                return self._parse_event(updated_event)

            return None

        except Exception as e:
            self.logger.error(
                event='CALENDAR_UPDATE_ERROR',
                message=f'Failed to update event: {str(e)}',
                event_id=event_id,
                error=str(e)
            )
            return None

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar identifier

        Returns:
            True if deleted successfully
        """
        if not self.service:
            return False

        try:
            result = self._execute_with_retry(
                lambda: self.service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
            )

            self.logger.info(
                event='CALENDAR_EVENT_DELETED',
                message=f'Deleted event: {event_id}',
                event_id=event_id
            )

            return True

        except Exception as e:
            self.logger.error(
                event='CALENDAR_DELETE_ERROR',
                message=f'Failed to delete event: {str(e)}',
                event_id=event_id,
                error=str(e)
            )
            return False

    def search_events(
        self,
        query: str,
        max_results: int = 10,
        calendar_id: str = 'primary'
    ) -> Optional[List[CalendarEvent]]:
        """
        Search events by query.

        Args:
            query: Search query
            max_results: Maximum results
            calendar_id: Calendar identifier

        Returns:
            List of matching CalendarEvent or None if failed
        """
        if not self.service:
            return None

        try:
            events_result = self._execute_with_retry(
                lambda: self.service.events().list(
                    calendarId=calendar_id,
                    q=query,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
            )

            if not events_result:
                return None

            events = events_result.get('items', [])
            return [self._parse_event(event) for event in events]

        except Exception as e:
            self.logger.error(
                event='CALENDAR_SEARCH_ERROR',
                message=f'Failed to search events: {str(e)}',
                query=query,
                error=str(e)
            )
            return None

    def _execute_with_retry(self, operation):
        """Execute operation with retry logic"""
        for attempt in range(self.max_retries):
            try:
                result = operation()
                self.metrics_logger.record_metric(
                    'calendar_api_success',
                    1,
                    {'attempt': attempt + 1}
                )
                return result

            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    # Retryable errors
                    wait_time = (2 ** attempt) * 1.0
                    self.logger.warning(
                        event='CALENDAR_API_RETRY',
                        message=f'API error {e.resp.status}, retrying in {wait_time}s',
                        status=e.resp.status,
                        attempt=attempt + 1
                    )
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    # Non-retryable error
                    self.logger.error(
                        event='CALENDAR_API_ERROR',
                        message=f'API error {e.resp.status}: {str(e)}',
                        status=e.resp.status
                    )
                    return None

            except Exception as e:
                self.logger.warning(
                    event='CALENDAR_API_UNEXPECTED_ERROR',
                    message=f'Unexpected error, attempt {attempt + 1}: {str(e)}',
                    error=str(e)
                )
                continue

        self.metrics_logger.record_metric('calendar_api_failure', 1)
        return None

    def _parse_event(self, event_data: Dict[str, Any]) -> CalendarEvent:
        """Parse API event data into CalendarEvent"""
        start = event_data.get('start', {})
        end = event_data.get('end', {})

        # Parse datetime
        start_dt = datetime.fromisoformat(
            start.get('dateTime', start.get('date', datetime.utcnow().isoformat())).replace('Z', '+00:00')
        )
        end_dt = datetime.fromisoformat(
            end.get('dateTime', end.get('date', datetime.utcnow().isoformat())).replace('Z', '+00:00')
        )

        # Parse attendees
        attendees = [
            a.get('email', '') for a in event_data.get('attendees', [])
        ]

        # Parse reminder
        reminders = event_data.get('reminders', {})
        reminder_minutes = None
        if not reminders.get('useDefault'):
            overrides = reminders.get('overrides', [])
            if overrides:
                reminder_minutes = overrides[0].get('minutes')

        return CalendarEvent(
            id=event_data.get('id', ''),
            summary=event_data.get('summary', 'Untitled'),
            description=event_data.get('description'),
            location=event_data.get('location'),
            start=start_dt,
            end=end_dt,
            attendees=attendees,
            reminder_minutes=reminder_minutes,
            created=datetime.fromisoformat(
                event_data.get('created', datetime.utcnow().isoformat()).replace('Z', '+00:00')
            ),
            updated=datetime.fromisoformat(
                event_data.get('updated', datetime.utcnow().isoformat()).replace('Z', '+00:00')
            ),
            creator_email=event_data.get('creator', {}).get('email', ''),
            organizer_email=event_data.get('organizer', {}).get('email', ''),
            html_link=event_data.get('htmlLink', '')
        )


def create_calendar_service(
    credentials_path: str,
    token_path: str,
    logger: EventLogger,
    metrics_logger: MetricsLogger
) -> GoogleCalendarService:
    """Factory function to create GoogleCalendarService"""
    return GoogleCalendarService(
        credentials_path=credentials_path,
        token_path=token_path,
        logger=logger,
        metrics_logger=metrics_logger
    )
