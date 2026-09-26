from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Broadcast, CapabilityProfile, Milestone
from .serializers import BroadcastSerializer, CapabilityProfileSerializer, MilestoneSerializer


class CapabilityProfileViewSet(viewsets.ModelViewSet):
    queryset = CapabilityProfile.objects.all().order_by("-created_at")
    serializer_class = CapabilityProfileSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "map"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        country = self.request.query_params.get("country")
        industry = self.request.query_params.get("industry")
        search = self.request.query_params.get("search")
        mine = self.request.query_params.get("mine")
        if country:
            qs = qs.filter(country__iexact=country)
        if industry:
            qs = qs.filter(industry__iexact=industry)
        if search:
            qs = qs.filter(name__icontains=search)
        if mine == "1" and self.request.user.is_authenticated:
            qs = qs.filter(owner=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def map(self, request):
        qs = CapabilityProfile.objects.all()
        industry = request.query_params.get("industry")
        if industry:
            qs = qs.filter(industry__iexact=industry)
        by_country = list(
            qs.values("country").annotate(count=Count("id")).order_by("country")
        )
        by_industry = list(
            CapabilityProfile.objects.values("industry").annotate(count=Count("id")).order_by("industry")
        )
        return Response({"by_country": by_country, "by_industry": by_industry, "total": qs.count()})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def request_verification(self, request, pk=None):
        profile = self.get_object()
        if profile.owner != request.user:
            return Response({"detail": "Only the owner can request verification."}, status=403)
        profile.verification_requested = True
        profile.save(update_fields=["verification_requested"])
        return Response({"verification_requested": True})


class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    http_method_names = ["get", "post", "delete"]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        profile_id = self.request.query_params.get("profile")
        if profile_id:
            qs = qs.filter(profile_id=profile_id)
        return qs

    def create(self, request):
        try:
            profile = CapabilityProfile.objects.get(id=request.data.get("profile_id"))
        except (CapabilityProfile.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "profile_id required"}, status=status.HTTP_400_BAD_REQUEST)
        if profile.owner != request.user:
            return Response({"detail": "Only the owner can post milestones."}, status=403)
        ms = Milestone.objects.create(
            profile=profile,
            kind=request.data.get("kind", "milestone"),
            title=request.data.get("title", "")[:200],
            detail=request.data.get("detail", ""),
        )
        return Response(MilestoneSerializer(ms).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.profile.owner != request.user:
            return Response({"detail": "Only the owner can delete."}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Admins only."}, status=403)
        obj = self.get_object()
        obj.is_verified = True
        obj.save(update_fields=["is_verified"])
        return Response({"is_verified": True})


class BroadcastViewSet(viewsets.ModelViewSet):
    queryset = Broadcast.objects.all()
    serializer_class = BroadcastSerializer
    http_method_names = ["get", "post", "delete"]

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        wanted = self.request.query_params.get("status", "open")
        if wanted in ("open", "closed"):
            qs = qs.filter(status=wanted)
        return qs

    def create(self, request):
        try:
            profile = CapabilityProfile.objects.get(id=request.data.get("author_profile_id"))
        except (CapabilityProfile.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "author_profile_id required"}, status=status.HTTP_400_BAD_REQUEST)
        if profile.owner != request.user:
            return Response({"detail": "Broadcast from your own profile only."}, status=403)
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
        b = Broadcast.objects.create(
            author_profile=profile, author=request.user, text=text[:2000],
            target_country=request.data.get("target_country", ""),
            industry=request.data.get("industry", ""),
        )
        return Response(BroadcastSerializer(b).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        obj = self.get_object()
        if obj.author != request.user:
            return Response({"detail": "Only the author can close."}, status=403)
        obj.status = "closed"
        obj.save(update_fields=["status"])
        return Response({"status": "closed"})

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != request.user:
            return Response({"detail": "Only the author can delete."}, status=403)
        return super().destroy(request, *args, **kwargs)
