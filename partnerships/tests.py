from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import CapabilityProfile

# Hermetic suite: never hit the live Gemini API from tests (slow + flaky).
# AI wiring itself is covered by explicit mocks below.
import os as _os
_os.environ.pop("GEMINI_API_KEY", None)


def token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class PartnershipTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "a@x.com", "pass12345")
        self.bob = User.objects.create_user("bob", "b@x.com", "pass12345")
        self.a_profile = CapabilityProfile.objects.create(
            owner=self.alice, name="Alice Foods", country="NG", industry="Agriculture",
            offers="Cassava products", needs="Distributor", partnership_type="Distribution")
        self.b_profile = CapabilityProfile.objects.create(
            owner=self.bob, name="Bob Distro", country="GH", industry="Logistics",
            offers="Distribution network", needs="Suppliers", partnership_type="Distribution",
            is_verified=True)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_for(user)}")

    def test_match_returns_scored_results(self):
        res = self.client.post("/api/match/", {
            "query": "I produce cassava in Nigeria and need a distributor in Ghana",
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["count"], 1)
        top = res.data["results"][0]
        self.assertIn("match_score", top)
        self.assertTrue(top["why"])

    def test_match_excludes_own_profiles(self):
        self.auth(self.alice)
        res = self.client.post("/api/match/", {"query": "distributor in Ghana"}, format="json")
        names = [r["name"] for r in res.data["results"]]
        self.assertNotIn("Alice Foods", names)
        self.assertIn("Bob Distro", names)

    def test_match_requires_query(self):
        self.assertEqual(self.client.post("/api/match/", {}, format="json").status_code, 400)

    def test_request_lifecycle_with_names(self):
        self.auth(self.alice)
        res = self.client.post("/api/requests/", {
            "from_profile": self.a_profile.id, "to_profile": self.b_profile.id,
            "partnership_type": "Distribution", "message": "Let's partner",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["to_profile_name"], "Bob Distro")
        rid = res.data["id"]

        # Receiver sees it in their inbox too
        self.auth(self.bob)
        inbox = self.client.get("/api/requests/")
        self.assertTrue(any(r["id"] == rid for r in inbox.data["results"]))

        accept = self.client.post(f"/api/requests/{rid}/accept/", {}, format="json")
        self.assertEqual(accept.data["status"], "accepted")

    def test_requests_require_auth(self):
        self.assertEqual(self.client.get("/api/requests/").status_code, 401)

    def test_brief(self):
        res = self.client.post("/api/brief/", {
            "from_profile_id": self.a_profile.id, "to_profile_id": self.b_profile.id,
        }, format="json")
        self.assertEqual(res.status_code, 200)
        for key in ("title", "opportunity", "benefits", "things_to_verify"):
            self.assertIn(key, res.data)

    def test_match_returns_intent_and_logs_query(self):
        from .models import MatchQuery
        res = self.client.post("/api/match/", {"query": "need a distributor in Ghana"}, format="json")
        self.assertIn("intent", res.data)
        self.assertIn("GH", res.data["intent"]["countries"])
        self.assertIn("ai", res.data)
        self.assertEqual(MatchQuery.objects.count(), 1)

    def test_metrics(self):
        self.client.post("/api/match/", {"query": "distributor Ghana"}, format="json")
        res = self.client.get("/api/metrics/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["profiles"], 2)
        self.assertEqual(res.data["searches"], 1)
        self.assertIn("request_conversion_pct", res.data)

    def test_notifications(self):
        self.auth(self.alice)
        self.client.post("/api/requests/", {
            "from_profile": self.a_profile.id, "to_profile": self.b_profile.id,
            "partnership_type": "Distribution", "message": "Hi",
        }, format="json")
        self.auth(self.bob)
        res = self.client.get("/api/notifications/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(n["kind"] == "request_received" for n in res.data))

    def test_match_partnership_type_filter(self):
        res = self.client.post("/api/match/", {
            "query": "partner", "partnership_type": "Logistics",
        }, format="json")
        self.assertTrue(all("Logistics" in (r["partnership_type"] or "") for r in res.data["results"]))

    def test_match_history(self):
        self.auth(self.alice)
        self.client.post("/api/match/", {"query": "distributor Ghana"}, format="json")
        res = self.client.get("/api/match/history/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any("distributor Ghana" in h["query"] for h in res.data))
        # other users don't see it
        self.auth(self.bob)
        res = self.client.get("/api/match/history/")
        self.assertEqual(res.data, [])

    def test_intent_cache_avoids_repeat_llm_calls(self):
        from unittest.mock import patch
        from linka import ai
        with patch.object(ai, "extract_intent_llm", return_value={"countries": ["GH"], "industries": [], "keywords": []}) as m:
            self.assertIsNotNone(ai.cached_llm_intent("need distributor in Ghana"))
            self.assertIsNotNone(ai.cached_llm_intent("  NEED distributor in ghana "))
            self.assertEqual(m.call_count, 1)

    def test_endorsement_flow(self):
        self.auth(self.alice)
        rid = self.client.post("/api/requests/", {
            "from_profile": self.a_profile.id, "to_profile": self.b_profile.id,
            "partnership_type": "Distribution", "message": "Let's partner",
        }, format="json").data["id"]
        # pending requests can't be endorsed
        bad = self.client.post("/api/endorsements/", {"request_id": rid, "rating": 5}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.auth(self.bob)
        self.client.post(f"/api/requests/{rid}/accept/", {}, format="json")
        # receiver endorses
        ok = self.client.post("/api/endorsements/",
                              {"request_id": rid, "rating": 5, "comment": "Smooth deal"}, format="json")
        self.assertEqual(ok.status_code, 201)
        # duplicate endorsement rejected
        dup = self.client.post("/api/endorsements/", {"request_id": rid, "rating": 4}, format="json")
        self.assertEqual(dup.status_code, 400)
        # rating surfaces on the profile
        prof = self.client.get(f"/api/profiles/{self.b_profile.id}/").data
        self.assertEqual(prof["rating"]["average"], 5.0)

    def test_mou_template_fallback(self):
        from unittest.mock import patch
        self.auth(self.alice)
        rid = self.client.post("/api/requests/", {
            "from_profile": self.a_profile.id, "to_profile": self.b_profile.id,
            "partnership_type": "Distribution", "message": "context",
        }, format="json").data["id"]
        # locked before acceptance
        self.assertEqual(self.client.post("/api/mou/", {"request_id": rid}, format="json").status_code, 400)
        self.auth(self.bob)
        self.client.post(f"/api/requests/{rid}/accept/", {}, format="json")
        with patch("linka.ai.generate_mou_llm", return_value=None):
            res = self.client.post("/api/mou/", {"request_id": rid}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("MEMORANDUM", res.data["markdown"])
        self.assertFalse(res.data["ai"])
        with patch("linka.ai.generate_mou_llm", return_value="# MOU draft"):
            res = self.client.post("/api/mou/", {"request_id": rid}, format="json")
        self.assertTrue(res.data["ai"])
        self.assertIn("MOU draft", res.data["markdown"])

    def test_trade_info(self):
        from unittest.mock import patch
        res = self.client.post("/api/trade-info/",
                               {"from_country": "NG", "to_country": "GH", "industry": "Agriculture"},
                               format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("certifications", res.data)
        self.assertIn("payments", res.data)
        with patch("linka.ai.generate_trade_llm", return_value={"tariff_note": "AI note", "certifications": ["X"], "payments": ["Y"]}):
            res = self.client.post("/api/trade-info/",
                                   {"from_country": "NG", "to_country": "GH", "industry": "Agriculture"},
                                   format="json")
        self.assertTrue(res.data["ai"])
        self.assertEqual(res.data["tariff_note"], "AI note")

    def test_voice_requires_audio(self):
        self.assertEqual(self.client.post("/api/voice-intent/", {}, format="json").status_code, 400)

    def test_voice_rejects_tiny_audio(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        tiny = SimpleUploadedFile("note.webm", b"\x1a\x45", content_type="audio/webm")
        res = self.client.post("/api/voice-intent/", {"audio": tiny})
        self.assertEqual(res.status_code, 400)

    def test_voice_rate_limit_returns_429(self):
        from unittest.mock import patch
        from django.core.files.uploadedfile import SimpleUploadedFile
        from linka.ai import RateLimited
        blob = SimpleUploadedFile("note.webm", b"\x1a\x45" * 1000, content_type="audio/webm")
        with patch("linka.ai.transcribe_audio_llm", side_effect=RateLimited("slow down")):
            res = self.client.post("/api/voice-intent/", {"audio": blob})
        self.assertEqual(res.status_code, 429)

    def test_gemini_retry_then_success(self):
        from unittest.mock import patch
        from urllib.error import HTTPError
        from linka import ai

        def fake_response():
            class R:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self): return b'{"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}'
            return R()

        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] < 3:
                raise HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
            return fake_response()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep") as nap:
            out = ai._post_gemini({"contents": []})
        self.assertEqual(out["candidates"][0]["content"]["parts"][0]["text"], "hi")
        self.assertEqual(calls["n"], 3)
        self.assertTrue(nap.called)
