from django.contrib import admin

from .models import Broadcast, CapabilityProfile, Milestone


@admin.register(CapabilityProfile)
class CapabilityProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "industry", "owner", "is_verified", "verification_requested", "registry_verified", "created_at")
    list_filter = ("country", "industry", "is_verified", "verification_requested", "registry_verified")
    search_fields = ("name", "city", "offers", "needs")
    actions = ("verify", "unverify")

    @admin.action(description="Mark selected profiles as verified")
    def verify(self, request, queryset):
        queryset.update(is_verified=True)

    @admin.action(description="Mark selected profiles as unverified")
    def unverify(self, request, queryset):
        queryset.update(is_verified=False)


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "kind", "is_verified", "created_at")
    list_filter = ("kind", "is_verified")
    actions = ("verify_milestones",)

    @admin.action(description="Mark selected milestones as verified")
    def verify_milestones(self, request, queryset):
        queryset.update(is_verified=True)


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("id", "author_profile", "target_country", "industry", "status", "created_at")
    list_filter = ("status", "target_country", "industry")
