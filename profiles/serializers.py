from rest_framework import serializers

from .models import Broadcast, CapabilityProfile, Milestone


class CapabilityProfileSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source="owner.username")
    rating = serializers.ReadOnlyField()

    class Meta:
        model = CapabilityProfile
        fields = "__all__"
        read_only_fields = ("id", "owner", "is_verified", "registry_verified", "created_at", "updated_at")


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = "__all__"
        read_only_fields = ("id", "profile", "is_verified", "created_at")


class BroadcastSerializer(serializers.ModelSerializer):
    author_profile_name = serializers.ReadOnlyField(source="author_profile.name")
    match_count = serializers.SerializerMethodField()

    class Meta:
        model = Broadcast
        fields = "__all__"
        read_only_fields = ("id", "author", "author_profile", "created_at")

    def get_match_count(self, obj):
        from partnerships.views import detect_intent
        from profiles.models import CapabilityProfile as CP
        intent = detect_intent(obj.text)
        qs = CP.objects.all()
        if obj.target_country:
            qs = qs.filter(country=obj.target_country)
        if obj.industry:
            qs = qs.filter(industry__iexact=obj.industry)
        n = 0
        for p in qs[:100]:
            hay = " ".join([p.industry, p.products_services, p.skills_expertise, p.offers]).lower()
            if set(intent["keywords"]) & set(hay.split()) or p.industry in intent["industries"]:
                n += 1
        return n
