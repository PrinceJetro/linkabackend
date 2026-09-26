from django.contrib import admin

from .models import Endorsement, PartnershipRequest


@admin.register(PartnershipRequest)
class PartnershipRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "from_profile", "to_profile", "partnership_type", "status", "created_at")
    list_filter = ("status", "partnership_type")
    search_fields = ("message",)


@admin.register(Endorsement)
class EndorsementAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
