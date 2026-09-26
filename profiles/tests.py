from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import CapabilityProfile


def make_user(username="owner"):
    return User.objects.create_user(username, f"{username}@x.com", "pass12345")


def make_profile(owner, name="Test Co", country="GH", industry="Logistics"):
    return CapabilityProfile.objects.create(
        owner=owner, name=name, country=country, city="Accra", industry=industry,
        offers="Distribution network", needs="Suppliers", partnership_type="Distribution",
    )


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("other")
        make_profile(self.user, "Mine")
        make_profile(self.other, "Theirs")

    def auth(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_is_public_and_paginated(self):
        res = self.client.get("/api/profiles/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data)
        self.assertEqual(res.data["count"], 2)

    def test_mine_filter(self):
        self.auth(self.user)
        res = self.client.get("/api/profiles/?mine=1")
        names = [p["name"] for p in res.data["results"]]
        self.assertEqual(names, ["Mine"])

    def test_create_requires_auth(self):
        res = self.client.post("/api/profiles/", {"name": "X"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_create_assigns_owner(self):
        self.auth(self.user)
        res = self.client.post("/api/profiles/", {
            "name": "New Co", "country": "KE", "industry": "Technology",
            "offers": "API", "needs": "Investors",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(CapabilityProfile.objects.get(name="New Co").owner, self.user)

    def test_map_stats(self):
        res = self.client.get("/api/profiles/map/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total"], 2)
        self.assertTrue(any(r["country"] == "GH" for r in res.data["by_country"]))

    def test_map_industry_filter(self):
        res = self.client.get("/api/profiles/map/?industry=Logistics")
        self.assertEqual(res.data["total"], 2)
        res = self.client.get("/api/profiles/map/?industry=Technology")
        self.assertEqual(res.data["total"], 0)

    def test_request_verification(self):
        self.auth(self.user)
        mine = CapabilityProfile.objects.get(name="Mine")
        res = self.client.post(f"/api/profiles/{mine.id}/request_verification/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        mine.refresh_from_db()
        self.assertTrue(mine.verification_requested)

    def test_request_verification_owner_only(self):
        self.auth(self.other)
        mine = CapabilityProfile.objects.get(name="Mine")
        res = self.client.post(f"/api/profiles/{mine.id}/request_verification/", {}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_milestones_owner_only_write(self):
        mine = CapabilityProfile.objects.get(name="Mine")
        # public list
        self.assertEqual(self.client.get(f"/api/profiles/milestones/?profile={mine.id}").status_code, 200)
        # anon cannot post
        res = self.client.post("/api/profiles/milestones/",
                               {"profile_id": mine.id, "kind": "shipment", "title": "Shipped 10t"}, format="json")
        self.assertEqual(res.status_code, 401)
        # non-owner cannot post
        self.auth(self.other)
        res = self.client.post("/api/profiles/milestones/",
                               {"profile_id": mine.id, "title": "Hijack"}, format="json")
        self.assertEqual(res.status_code, 403)
        # owner can
        self.auth(self.user)
        res = self.client.post("/api/profiles/milestones/",
                               {"profile_id": mine.id, "kind": "shipment",
                                "title": "Dispatched 10 tons Lagos→Tema"}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_registry_verified_is_read_only(self):
        self.auth(self.user)
        mine = CapabilityProfile.objects.get(name="Mine")
        res = self.client.patch(f"/api/profiles/{mine.id}/",
                                {"registry_verified": True, "registry_name": "CAC",
                                 "registration_number": "RC123"}, format="json")
        self.assertEqual(res.status_code, 200)
        mine.refresh_from_db()
        self.assertFalse(mine.registry_verified)
        self.assertEqual(mine.registry_name, "CAC")

    def test_broadcast_lifecycle(self):
        mine = CapabilityProfile.objects.get(name="Mine")
        self.auth(self.user)
        res = self.client.post("/api/profiles/broadcasts/", {
            "author_profile_id": mine.id,
            "text": "Urgent: need cold-chain warehouse in Nairobi for 30 days",
            "target_country": "KE", "industry": "Logistics",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        bid = res.data["id"]
        self.assertGreaterEqual(res.data["match_count"], 0)
        # open wall lists it
        wall = self.client.get("/api/profiles/broadcasts/")
        self.assertTrue(any(b["id"] == bid for b in wall.data["results"]))
        # close it
        close = self.client.post(f"/api/profiles/broadcasts/{bid}/close/", {}, format="json")
        self.assertEqual(close.data["status"], "closed")
