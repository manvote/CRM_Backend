from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CalendarEventViewSet,
    RecurringEventViewSet,
    EventReminderViewSet,
)

app_name = 'calendar'

router = DefaultRouter()
router.register(r'events', CalendarEventViewSet, basename='calendar-event')
router.register(r'recurring-events', RecurringEventViewSet, basename='recurring-event')
router.register(r'reminders', EventReminderViewSet, basename='event-reminder')

urlpatterns = [
    path('', include(router.urls)),
]
