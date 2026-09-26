from rest_framework.routers import DefaultRouter

from .views import BroadcastViewSet, CapabilityProfileViewSet, MilestoneViewSet

router = DefaultRouter()
# Specific prefixes first: the "" detail route is greedy and would swallow them.
router.register("milestones", MilestoneViewSet, basename="milestones")
router.register("broadcasts", BroadcastViewSet, basename="broadcasts")
router.register("", CapabilityProfileViewSet, basename="profiles")

urlpatterns = router.urls
