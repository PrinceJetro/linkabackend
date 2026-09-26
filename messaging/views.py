from django.contrib.auth.models import User
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source="sender.username")

    class Meta:
        model = Message
        fields = ("id", "sender", "sender_name", "body", "is_read", "created_at")
        read_only_fields = ("id", "sender", "is_read", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    other_username = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "other_username", "last_message", "unread_count", "updated_at")

    def _user(self):
        return self.context["request"].user

    def get_other_username(self, obj):
        other = obj.other(self._user())
        return other.username if other else "—"

    def get_last_message(self, obj):
        last = obj.messages.last()
        return {"body": last.body, "sender_name": last.sender.username} if last else None

    def get_unread_count(self, obj):
        return obj.messages.filter(is_read=False).exclude(sender=self._user()).count()


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def create(self, request):
        """Start (or reopen) a 1:1 conversation with another user.

        Body: {"username": "<them>"} or {"user_id": N}.
        """
        username = request.data.get("username")
        user_id = request.data.get("user_id")
        try:
            other = User.objects.get(username=username) if username else User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Target user not found."}, status=404)
        if other == request.user:
            return Response({"detail": "You cannot message yourself."}, status=400)
        existing = Conversation.objects.filter(participants=request.user).filter(participants=other).first()
        convo = existing or Conversation.objects.create()
        if not existing:
            convo.participants.add(request.user, other)
        return Response(ConversationSerializer(convo, context={"request": request}).data,
                        status=200 if existing else 201)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        convo = self.get_object()
        if request.method == "GET":
            convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
            msgs = convo.messages.all()
            return Response(MessageSerializer(msgs, many=True).data)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body is required"}, status=400)
        msg = Message.objects.create(conversation=convo, sender=request.user, body=body[:2000])
        convo.save(update_fields=["updated_at"])  # bump thread ordering
        return Response(MessageSerializer(msg).data, status=201)
