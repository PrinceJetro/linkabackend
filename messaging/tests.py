from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Conversation


def token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class MessagingTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "a@x.com", "pass12345")
        self.bob = User.objects.create_user("bob", "b@x.com", "pass12345")
        self.eve = User.objects.create_user("eve", "e@x.com", "pass12345")

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_for(user)}")

    def test_start_lists_send_read(self):
        self.auth(self.alice)
        res = self.client.post("/api/conversations/", {"username": "bob"}, format="json")
        self.assertEqual(res.status_code, 201)
        cid = res.data["id"]

        # reopening returns the same thread
        again = self.client.post("/api/conversations/", {"username": "bob"}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data["id"], cid)

        sent = self.client.post(f"/api/conversations/{cid}/messages/", {"body": "Hello Bob"}, format="json")
        self.assertEqual(sent.status_code, 201)

        self.auth(self.bob)
        threads = self.client.get("/api/conversations/")
        self.assertEqual(threads.data["results"][0]["unread_count"], 1)
        msgs = self.client.get(f"/api/conversations/{cid}/messages/")
        self.assertEqual(msgs.data[0]["body"], "Hello Bob")
        # reading marks as read
        threads = self.client.get("/api/conversations/")
        self.assertEqual(threads.data["results"][0]["unread_count"], 0)

    def test_cannot_message_self_or_missing_user(self):
        self.auth(self.alice)
        self.assertEqual(self.client.post("/api/conversations/", {"username": "alice"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/conversations/", {"username": "ghost"}, format="json").status_code, 404)

    def test_stranger_cannot_access_thread(self):
        self.auth(self.alice)
        cid = self.client.post("/api/conversations/", {"username": "bob"}, format="json").data["id"]
        self.auth(self.eve)
        self.assertEqual(self.client.get(f"/api/conversations/{cid}/messages/").status_code, 404)
        self.assertEqual(self.client.get("/api/conversations/").data["count"], 0)

    def test_requires_auth(self):
        self.assertEqual(self.client.get("/api/conversations/").status_code, 401)
