from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

User = settings.AUTH_USER_MODEL


# ============================
# ENUMS / CHOICES
# ============================

class EventType(models.TextChoices):
    EVENT = 'event', 'Event'
    TASK = 'task', 'Task'
    MEETING = 'meeting', 'Meeting'
    SCHEDULED = 'scheduled', 'Scheduled'
    TASK_REMINDER = 'task_reminder', 'Task Reminder'


class EventPriority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'


# ============================
# MAIN CALENDAR EVENT MODEL
# ============================

class CalendarEvent(models.Model):
    """
    Unified Calendar Event model
    (Merged old Event + new CalendarEvent)
    """

    # Basic info (OLD + NEW)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.EVENT
    )

    # Calendar time slots (Figma based)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    duration_minutes = models.IntegerField(editable=False, null=True)

    # User relations
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_calendar_events'
    )
    attendees = models.ManyToManyField(
        User,
        related_name='attending_calendar_events',
        blank=True
    )

    # OLD CODE SUPPORT (task & meeting linking)
    task_id = models.IntegerField(blank=True, null=True)
    meeting_id = models.IntegerField(blank=True, null=True)

    # Extra event details (NEW)
    location = models.CharField(max_length=255, blank=True, null=True)
    color_code = models.CharField(max_length=7, default='#22c55e')
    priority = models.CharField(
        max_length=10,
        choices=EventPriority.choices,
        default=EventPriority.MEDIUM
    )
    is_all_day = models.BooleanField(default=False)

    reminder_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minutes before event to trigger reminder"
    )

    is_completed = models.BooleanField(default=False)

    # CRM integration
    #related_lead = models.ForeignKey(
        #'crm.Lead',
        #on_delete=models.SET_NULL,
        #null=True,
        #blank=True,
        #related_name='calendar_events'
    #)
    #related_deal = models.ForeignKey(
        #'crm.Deal',
        #on_delete=models.SET_NULL,
        #null=True,
        #blank=True,
        #related_name='calendar_events'
    #)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # MODEL CONFIG
    # ============================

    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'end_datetime']),
            models.Index(fields=['event_type']),
            models.Index(fields=['created_by']),
        ]

    # ============================
    # VALIDATION & HELPERS
    # ============================

    def clean(self):
        if self.end_datetime <= self.start_datetime:
            raise ValidationError("End time must be after start time")

    def save(self, *args, **kwargs):
        if self.start_datetime and self.end_datetime:
            duration = self.end_datetime - self.start_datetime
            self.duration_minutes = int(duration.total_seconds() / 60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.start_datetime.strftime('%Y-%m-%d %H:%M')})"

    @property
    def is_past(self):
        return self.end_datetime < timezone.now()

    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime


# ============================
# RECURRING EVENTS
# ============================

class RecurringEvent(models.Model):
    """
    Recurring event configuration
    """

    class RecurrencePattern(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    base_event = models.OneToOneField(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='recurrence'
    )

    pattern = models.CharField(
        max_length=10,
        choices=RecurrencePattern.choices
    )

    interval = models.PositiveIntegerField(
        default=1,
        help_text="Repeat every X days/weeks/months"
    )

    end_date = models.DateField(null=True, blank=True)
    occurrences = models.PositiveIntegerField(null=True, blank=True)

    weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text="Weekday numbers (0=Monday, 6=Sunday)"
    )

    def __str__(self):
        return f"Recurring {self.base_event.title} ({self.pattern})"


# ============================
# EVENT REMINDERS
# ============================

class EventReminder(models.Model):
    """
    Reminder per user per event
    """

    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='reminders'
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    reminder_datetime = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['reminder_datetime']
        unique_together = ['event', 'user', 'reminder_datetime']

    def __str__(self):
        return f"Reminder: {self.event.title} @ {self.reminder_datetime}"
