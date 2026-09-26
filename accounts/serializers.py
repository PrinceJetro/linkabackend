from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import CapabilityProfile

ACCOUNT_TYPES = ("Business", "Investor", "Researcher", "Distributor", "Manufacturer", "Other")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # Business context (write-only): used to seed the first capability profile
    organization = serializers.CharField(write_only=True, required=False, default="", allow_blank=True)
    account_type = serializers.ChoiceField(choices=[(t, t) for t in ACCOUNT_TYPES], write_only=True, required=False, default="Business")
    country = serializers.ChoiceField(choices=CapabilityProfile.COUNTRIES, write_only=True, required=False, default="NG")
    city = serializers.CharField(write_only=True, required=False, default="", allow_blank=True)
    industry = serializers.ChoiceField(choices=[(i[0], i[0]) for i in CapabilityProfile.INDUSTRIES], write_only=True, required=False, default="Agriculture")

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "organization", "account_type", "country", "city", "industry")
        extra_kwargs = {"first_name": {"required": False}}

    def create(self, validated_data):
        organization = validated_data.pop("organization", "")
        account_type = validated_data.pop("account_type", "Business")
        country = validated_data.pop("country", "NG")
        city = validated_data.pop("city", "")
        industry = validated_data.pop("industry", "Agriculture")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # Seed the user's first capability profile so they can match + connect immediately
        CapabilityProfile.objects.create(
            owner=user,
            name=organization or user.username,
            country=country,
            city=city,
            industry=industry,
            partnership_type=account_type,
            offers="",
            needs="",
        )
        return user

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            "id": instance.id,
            "username": instance.username,
            "email": instance.email,
            "first_name": instance.first_name,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name")
        read_only_fields = ("id", "username")
