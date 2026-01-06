from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CalendarEvent, RecurringEvent, EventReminder

User = get_user_model()


# ============================
# USER (MINIMAL)
# ============================

class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info (used for attendees & creator)"""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


# ============================
# CALENDAR EVENT (DETAIL)
# ============================

class CalendarEventSerializer(serializers.ModelSerializer):
    """
    Full event serializer (merged old + new)
    """

    created_by_detail = UserMinimalSerializer(
        source='created_by',
        read_only=True
    )
    attendees_detail = UserMinimalSerializer(
        source='attendees',
        many=True,
        read_only=True
    )

    is_past = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()

    class Meta:
        model = CalendarEvent
        fields = [
            'id',

            # basic info
            'title',
            'description',
            'event_type',

            # time
            'start_datetime',
            'end_datetime',
            'duration_minutes',

            # users
            'created_by',
            'created_by_detail',
            'attendees',
            'attendees_detail',

            # old Event support
            'task_id',
            'meeting_id',

            # extra fields
            'location',
            'color_code',
            'priority',
            'is_all_day',
            'reminder_minutes',
            'is_completed',

            # CRM
            # CRM (disabled until CRM models exist)

            # metadata
            'created_at',
            'updated_at',

            # computed
            'is_past',
            'is_ongoing',
        ]

        read_only_fields = [
            'id',
            'created_by',
            'duration_minutes',
            'created_at',
            'updated_at',
        ]

    # ----------------------------
    # VALIDATION
    # ----------------------------

    def validate(self, data):
        start = data.get('start_datetime')
        end = data.get('end_datetime')

        if start and end and end <= start:
            raise serializers.ValidationError(
                "End datetime must be after start datetime"
            )
        return data

    # ----------------------------
    # CREATE
    # ----------------------------

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


# ============================
# CALENDAR EVENT (CREATE)
# ============================

class CalendarEventCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for create/update
    (used by frontend forms)
    """

    class Meta:
        model = CalendarEvent
        fields = [
            'title',
            'description',
            'event_type',
            'start_datetime',
            'end_datetime',

            # old Event fields
            'task_id',
            'meeting_id',

            # new fields
            'attendees',
            'location',
            'color_code',
            'priority',
            'is_all_day',
            'reminder_minutes',

            # CRM
            #'related_lead',
            #'related_deal',
        ]


# ============================
# CALENDAR EVENT (LIST)
# ============================

class CalendarEventListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for calendar list / month view
    """

    duration_minutes = serializers.ReadOnlyField()
    attendee_count = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            'id',
            'title',
            'event_type',
            'start_datetime',
            'end_datetime',
            'duration_minutes',
            'color_code',
            'is_completed',
            'attendee_count',
        ]

    def get_attendee_count(self, obj):
        return obj.attendees.count()


# ============================
# RECURRING EVENTS
# ============================

class RecurringEventSerializer(serializers.ModelSerializer):
    base_event = CalendarEventSerializer(read_only=True)

    class Meta:
        model = RecurringEvent
        fields = [
            'id',
            'base_event',
            'pattern',
            'interval',
            'end_date',
            'occurrences',
            'weekdays',
        ]


# ============================
# EVENT REMINDERS
# ============================

class EventReminderSerializer(serializers.ModelSerializer):
    event_detail = CalendarEventSerializer(
        source='event',
        read_only=True
    )

    class Meta:
        model = EventReminder
        fields = [
            'id',
            'event',
            'event_detail',
            'user',
            'reminder_datetime',
            'is_sent',
            'sent_at',
        ]

        read_only_fields = [
            'id',
            'is_sent',
            'sent_at',
        ]
