from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from profiles.models import CapabilityProfile


class AuthTests(APITestCase):
    def test_register_returns_jwt_and_seeds_profile(self):
        res = self.client.post("/api/auth/register/", {
            "username": "ama", "email": "a@x.com", "password": "strongpass1",
            "organization": "Ama Foods", "country": "NG", "industry": "Agriculture",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        profile = CapabilityProfile.objects.get(owner__username="ama")
        self.assertEqual(profile.name, "Ama Foods")
        self.assertEqual(profile.country, "NG")

    def test_register_rejects_short_password(self):
        res = self.client.post("/api/auth/register/", {
            "username": "bob", "email": "b@x.com", "password": "short",
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_login_and_me(self):
        User.objects.create_user("kofi", "k@x.com", "pass12345")
        res = self.client.post("/api/auth/login/", {"username": "kofi", "password": "pass12345"}, format="json")
        self.assertEqual(res.status_code, 200)
        token = res.data["access"]
        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "kofi")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_change_password(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        user = User.objects.create_user("kofi2", "k2@x.com", "oldpass123")
        token = str(RefreshToken.for_user(user).access_token)
        res = self.client.post("/api/auth/change_password/",
                               {"old_password": "wrong", "new_password": "newpass123"},
                               format="json", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/auth/change_password/",
                               {"old_password": "oldpass123", "new_password": "newpass123"},
                               format="json", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass123"))
