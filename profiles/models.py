from django.contrib.auth.models import User
from django.db import models


class CapabilityProfile(models.Model):
    COUNTRIES = [
        ("NG", "Nigeria"),
        ("GH", "Ghana"),
        ("KE", "Kenya"),
        ("RW", "Rwanda"),
        ("ZA", "South Africa"),
        ("EG", "Egypt"),
        ("OTHER", "Other"),
    ]
    INDUSTRIES = [
        ("Agriculture", "Agriculture"),
        ("Technology", "Technology"),
        ("Manufacturing", "Manufacturing"),
        ("Logistics", "Logistics"),
        ("Healthcare", "Healthcare"),
        ("Education", "Education"),
        ("Finance", "Finance"),
        ("Creative", "Creative industries"),
        ("Research", "Research"),
        ("Natural resources", "Natural resources"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    name = models.CharField(max_length=200)  # person / organization
    country = models.CharField(max_length=10, choices=COUNTRIES, default="NG")
    city = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=50, choices=INDUSTRIES, default="Agriculture")
    products_services = models.TextField(blank=True)
    skills_expertise = models.TextField(blank=True)
    offers = models.TextField(help_text="What they can offer")
    needs = models.TextField(blank=True, help_text="What they need")
    partnership_type = models.CharField(max_length=100, blank=True)
    target_countries = models.JSONField(default=list, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_requested = models.BooleanField(default=False)
    avatar_url = models.URLField(blank=True, default="", help_text="Optional logo/photo URL")
    registry_name = models.CharField(max_length=120, blank=True, help_text="e.g. CAC Nigeria, Registrar General Ghana, RDB Rwanda")
    registration_number = models.CharField(max_length=120, blank=True)
    registry_verified = models.BooleanField(default=False, help_text="Admin confirms the business registry entry")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.country} · {self.industry})"

    @property
    def rating(self):
        from partnerships.models import Endorsement
        qs = Endorsement.objects.filter(request__to_profile=self) | Endorsement.objects.filter(request__from_profile=self)
        avg = qs.aggregate(models.Avg("rating"))["rating__avg"]
        return {"average": round(avg, 1) if avg else None, "count": qs.count()}


class Milestone(models.Model):
    """Proof-of-capability timeline entries on a profile (shipments, certifications, capacity...)."""
    KINDS = [
        ("milestone", "Operational milestone"),
        ("shipment", "Trade & shipment proof"),
        ("certification", "Certification & quality"),
        ("partnership", "Partnership announcement"),
    ]
    profile = models.ForeignKey(CapabilityProfile, on_delete=models.CASCADE, related_name="milestones")
    kind = models.CharField(max_length=20, choices=KINDS, default="milestone")
    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile.name}: {self.title[:60]}"


class Broadcast(models.Model):
    """Live intent wall: urgent demand posts that AI matches against supplier profiles."""
    STATUS = [("open", "Open"), ("closed", "Closed")]
    author_profile = models.ForeignKey(CapabilityProfile, on_delete=models.CASCADE, related_name="broadcasts")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="broadcasts")
    text = models.TextField()
    target_country = models.CharField(max_length=10, choices=CapabilityProfile.COUNTRIES, blank=True, default="")
    industry = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author_profile.name}: {self.text[:60]} [{self.status}]"
