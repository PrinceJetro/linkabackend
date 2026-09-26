from django.contrib.auth.models import User
from django.db import models

from profiles.models import CapabilityProfile


class PartnershipRequest(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("info_requested", "Info requested"),
    ]

    from_profile = models.ForeignKey(
        CapabilityProfile, on_delete=models.CASCADE, related_name="sent_requests"
    )
    to_profile = models.ForeignKey(
        CapabilityProfile, on_delete=models.CASCADE, related_name="received_requests"
    )
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="partnership_requests")
    partnership_type = models.CharField(max_length=100, default="Distribution")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_profile} -> {self.to_profile} [{self.status}]"


class MatchQuery(models.Model):
    """Log of matcher searches — powers the metrics endpoint (slide: 'We measure...')."""

    query = models.TextField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    result_count = models.IntegerField(default=0)
    top_score = models.IntegerField(default=0)
    ai_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.query[:60]} ({self.result_count} results)"


class Endorsement(models.Model):
    """Verified partner review after an ACCEPTED partnership request completes."""

    request = models.ForeignKey(PartnershipRequest, on_delete=models.CASCADE, related_name="endorsements")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="endorsements")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("request", "reviewer")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reviewer.username} rated {self.request} {self.rating}/5"
