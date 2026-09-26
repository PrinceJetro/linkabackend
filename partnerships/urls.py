from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EndorsementViewSet, PartnershipRequestViewSet, generate_mou, match_history,
    match_partners, metrics, notifications, partnership_brief, trade_info, voice_intent,
)

router = DefaultRouter()
router.register("requests", PartnershipRequestViewSet, basename="requests")
router.register("endorsements", EndorsementViewSet, basename="endorsements")

urlpatterns = [
    path("match/", match_partners, name="match"),
    path("match/history/", match_history, name="match-history"),
    path("brief/", partnership_brief, name="brief"),
    path("mou/", generate_mou, name="mou"),
    path("trade-info/", trade_info, name="trade-info"),
    path("voice-intent/", voice_intent, name="voice-intent"),
    path("metrics/", metrics, name="metrics"),
    path("notifications/", notifications, name="notifications"),
] + router.urls
