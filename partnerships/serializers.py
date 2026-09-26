from rest_framework import serializers

from .models import PartnershipRequest


class PartnershipRequestSerializer(serializers.ModelSerializer):
    from_profile_name = serializers.ReadOnlyField(source="from_profile.name")
    to_profile_name = serializers.ReadOnlyField(source="to_profile.name")
    from_country = serializers.ReadOnlyField(source="from_profile.country")
    to_country = serializers.ReadOnlyField(source="to_profile.country")

    class Meta:
        model = PartnershipRequest
        fields = "__all__"
        read_only_fields = ("id", "requester", "status", "created_at")
