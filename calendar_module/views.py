from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
import pytz

from django.contrib.auth import get_user_model

from .models import CalendarEvent, RecurringEvent, EventReminder
from .serializers import (
    CalendarEventSerializer,
    CalendarEventListSerializer,
    CalendarEventCreateSerializer,
    RecurringEventSerializer,
    EventReminderSerializer,
)

User = get_user_model()


# ======================================================
# CALENDAR EVENTS
# ======================================================

class CalendarEventViewSet(viewsets.ModelViewSet):
    """
    Unified ViewSet for Events / Tasks / Meetings
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_datetime', 'created_at', 'priority']
    ordering = ['start_datetime']

    # ----------------------------
    # QUERYSET
    # ----------------------------

    def get_queryset(self):
        queryset = CalendarEvent.objects.filter(
            Q(created_by=self.request.user) |
            Q(attendees=self.request.user)
        ).distinct()

        # filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        # filter by completion
        is_completed = self.request.query_params.get('is_completed')
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed.lower() == 'true')

        # old-style calendar filters (day / week / month)
        date = self.request.query_params.get('date')
        view_type = self.request.query_params.get('view')  # day / week / month

        if date and view_type:
            date = parse_date(date)

            if date:
                if view_type == 'day':
                    queryset = queryset.filter(start_datetime__date=date)

                elif view_type == 'week':
                    week = date.isocalendar()[1]
                    queryset = queryset.filter(start_datetime__week=week)

                elif view_type == 'month':
                    queryset = queryset.filter(
                        start_datetime__year=date.year,
                        start_datetime__month=date.month
                    )

        return queryset.select_related(
            'created_by'
        ).prefetch_related('attendees')

    # ----------------------------
    # SERIALIZER SELECTION
    # ----------------------------

    def get_serializer_class(self):
        if self.action == 'list':
            return CalendarEventListSerializer
        if self.action == 'create':
            return CalendarEventCreateSerializer
        return CalendarEventSerializer

    # ----------------------------
    # CREATE
    # ----------------------------

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # ==================================================
    # CUSTOM ACTIONS
    # ==================================================

    @action(detail=False, methods=['get'])
    def week_view(self, request):
        """
        Week calendar view
        ?date=YYYY-MM-DD
        """
        date_str = request.query_params.get('date')
        date = parse_date(date_str) if date_str else timezone.now().date()

        if not date:
            return Response(
                {'error': 'Invalid date format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        tz = pytz.timezone(
            getattr(getattr(request.user, 'profile', None), 'timezone', 'UTC')
        )

        start_dt = tz.localize(datetime.combine(start_of_week, datetime.min.time()))
        end_dt = tz.localize(datetime.combine(end_of_week, datetime.max.time()))

        events = self.get_queryset().filter(
            start_datetime__gte=start_dt,
            start_datetime__lte=end_dt
        )

        serializer = CalendarEventListSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def month_view(self, request):
        """
        Month calendar view
        ?year=2026&month=1
        """
        try:
            year = int(request.query_params.get('year', timezone.now().year))
            month = int(request.query_params.get('month', timezone.now().month))
        except ValueError:
            return Response(
                {'error': 'Invalid year or month'},
                status=status.HTTP_400_BAD_REQUEST
            )

        first_day = datetime(year, month, 1)
        last_day = (
            datetime(year + 1, 1, 1) - timedelta(seconds=1)
            if month == 12
            else datetime(year, month + 1, 1) - timedelta(seconds=1)
        )

        tz = pytz.timezone(
            getattr(getattr(request.user, 'profile', None), 'timezone', 'UTC')
        )

        start_dt = tz.localize(first_day)
        end_dt = tz.localize(last_day)

        events = self.get_queryset().filter(
            start_datetime__gte=start_dt,
            start_datetime__lte=end_dt
        )

        serializer = CalendarEventListSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        event = self.get_object()
        event.is_completed = True
        event.save()
        return Response(CalendarEventSerializer(event).data)

    @action(detail=True, methods=['post'])
    def add_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            event.attendees.add(user)
            return Response(CalendarEventSerializer(event).data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_attendee(self, request, pk=None):
        event = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            event.attendees.remove(user)
            return Response(CalendarEventSerializer(event).data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ======================================================
# RECURRING EVENTS
# ======================================================

class RecurringEventViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RecurringEvent.objects.filter(
            base_event__created_by=self.request.user
        )


# ======================================================
# EVENT REMINDERS
# ======================================================

class EventReminderViewSet(viewsets.ModelViewSet):
    serializer_class = EventReminderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EventReminder.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.now()
        next_24h = now + timedelta(hours=24)

        reminders = self.get_queryset().filter(
            reminder_datetime__gte=now,
            reminder_datetime__lte=next_24h,
            is_sent=False
        )

        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)
