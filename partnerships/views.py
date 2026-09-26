import re

from django.db.models import Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from profiles.models import CapabilityProfile
from profiles.serializers import CapabilityProfileSerializer

from linka.ai import cached_llm_intent

from .models import Endorsement, MatchQuery, PartnershipRequest
from .serializers import PartnershipRequestSerializer

STOPWORDS = {
    "i", "am", "a", "an", "the", "in", "on", "for", "to", "of", "and", "or",
    "we", "our", "need", "needs", "want", "looking", "with", "from", "into",
    "who", "can", "help", "us", "me", "my", "produce", "lookingfor",
}

COUNTRY_KEYWORDS = {
    "ghana": "GH", "gh": "GH",
    "nigeria": "NG", "nigerian": "NG",
    "kenya": "KE", "kenyan": "KE",
    "rwanda": "RW", "rwandan": "RW",
    "south africa": "ZA", "south-africa": "ZA",
    "egypt": "EG", "egyptian": "EG",
}

INDUSTRY_KEYWORDS = {
    "agriculture": "Agriculture", "cassava": "Agriculture", "food": "Agriculture", "retail": "Agriculture",
    "technology": "Technology", "tech": "Technology", "payments": "Technology", "software": "Technology",
    "manufacturing": "Manufacturing", "manufacturer": "Manufacturing", "packaging": "Manufacturing", "pharma": "Healthcare",
    "logistics": "Logistics", "distribution": "Logistics", "distributor": "Logistics", "freight": "Logistics", "customs": "Logistics",
    "healthcare": "Healthcare", "pharmaceutical": "Healthcare",
    "finance": "Finance", "investor": "Finance",
    "research": "Research", "education": "Education",
}


def tokenize(text: str) -> set:
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    return words - STOPWORDS


def detect_intent(query: str) -> dict:
    """Rule-based intent extraction: countries, industries, keywords.

    Used directly, and as fallback when the Gemini API key is absent.
    Returns e.g. {"countries": ["GH"], "industries": ["Logistics"], "keywords": [...]}.
    """
    q = query.lower()
    countries = sorted({code for keyword, code in COUNTRY_KEYWORDS.items() if keyword in q})
    industries = sorted({ind for keyword, ind in INDUSTRY_KEYWORDS.items() if keyword in q})
    return {"countries": countries, "industries": industries, "keywords": sorted(tokenize(query))}


def score_profile(query: str, profile: CapabilityProfile, intent: dict | None = None):
    """Intent matcher: rule-based scoring over detected (or LLM-extracted) intent."""
    q = query.lower()
    intent = intent or detect_intent(query)
    q = query.lower()
    haystack = " ".join([
        profile.name, profile.industry, profile.products_services,
        profile.skills_expertise, profile.offers, profile.partnership_type,
    ]).lower()
    hay_tokens = tokenize(haystack)

    score = 50
    reasons = []

    if profile.country in intent["countries"]:
        score += 18
        reasons.append(f"Located in target market ({profile.get_country_display()})")

    if profile.industry in intent["industries"]:
        score += 14
        reasons.append(f"{profile.industry} capability matches your requirement")

    overlap = set(intent["keywords"]) & hay_tokens
    score += min(len(overlap) * 3, 15)
    if overlap:
        reasons.append(f"Overlapping capabilities: {', '.join(sorted(overlap)[:4])}")

    if profile.partnership_type and profile.partnership_type.lower() in q:
        score += 6
        reasons.append(f"Accepts {profile.partnership_type} partnerships")

    if profile.is_verified:
        score += 3
        reasons.append("Verified profile")

    if not reasons:
        reasons.append(f"Active {profile.industry} profile in {profile.get_country_display()}")

    return min(score, 98), reasons


class PartnershipRequestViewSet(viewsets.ModelViewSet):
    queryset = PartnershipRequest.objects.all().order_by("-created_at")
    serializer_class = PartnershipRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(
            Q(requester=user) | Q(to_profile__owner=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        obj = self.get_object()
        obj.status = "accepted"
        obj.save()
        return Response({"status": obj.status})

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        obj = self.get_object()
        obj.status = "declined"
        obj.save()
        return Response({"status": obj.status})

    @action(detail=True, methods=["post"])
    def request_info(self, request, pk=None):
        obj = self.get_object()
        obj.status = "info_requested"
        obj.save()
        return Response({"status": obj.status})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def match_partners(request):
    """Feature 2 — AI Partnership Matcher.

    Intent comes from Gemini when GEMINI_API_KEY is set, else rule-based.
    Every search is logged to MatchQuery for the metrics endpoint.
    """
    query = request.data.get("query", "").strip()
    if not query:
        return Response({"detail": "query is required"}, status=status.HTTP_400_BAD_REQUEST)

    country = request.data.get("country")
    industry = request.data.get("industry")
    partnership_type = request.data.get("partnership_type")
    qs = CapabilityProfile.objects.all()
    if request.user.is_authenticated:
        # Never match people with themselves
        qs = qs.exclude(owner=request.user)
    if country:
        qs = qs.filter(country__iexact=country)
    if industry:
        qs = qs.filter(industry__iexact=industry)
    if partnership_type:
        qs = qs.filter(partnership_type__icontains=partnership_type)

    llm_intent = cached_llm_intent(query)
    intent = llm_intent or detect_intent(query)

    scored = []
    for profile in qs[:100]:
        score, reasons = score_profile(query, profile, intent)
        scored.append((score, profile, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, profile, reasons in scored[:5]:
        data = CapabilityProfileSerializer(profile).data
        data["match_score"] = score
        data["why"] = reasons
        results.append(data)

    MatchQuery.objects.create(
        query=query[:2000],
        user=request.user if request.user.is_authenticated else None,
        result_count=len(results),
        top_score=results[0]["match_score"] if results else 0,
        ai_used=llm_intent is not None,
    )
    return Response({
        "query": query, "count": len(results), "results": results,
        "intent": intent, "ai": llm_intent is not None,
    })


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def partnership_brief(request):
    """Feature 5 — AI Partnership Brief (Gemini when configured, template fallback)."""
    from_id = request.data.get("from_profile_id")
    to_id = request.data.get("to_profile_id")
    objective = request.data.get("objective", "Cross-border expansion")
    try:
        a = CapabilityProfile.objects.get(id=from_id)
        b = CapabilityProfile.objects.get(id=to_id)
    except CapabilityProfile.DoesNotExist:
        return Response(
            {"detail": "from_profile_id and to_profile_id must be valid profile IDs"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    from linka.ai import generate_brief_llm
    language = request.data.get("language", "English")
    ai = generate_brief_llm(
        {"name": a.name, "country": a.get_country_display(), "offers": a.offers or a.products_services},
        {"name": b.name, "country": b.get_country_display(), "offers": b.offers or b.products_services},
        objective,
        language=language if language in ("English", "French", "Swahili", "Portuguese") else "English",
    )
    brief = {
        "title": f"{a.get_country_display()} → {b.get_country_display()} Partnership",
        "objective": objective,
        "company_a": {"name": a.name, "country": a.get_country_display(), "offers": a.offers},
        "company_b": {"name": b.name, "country": b.get_country_display(), "offers": b.offers},
        "opportunity": (ai or {}).get("opportunity") or f"{a.name} can supply {a.products_services or a.offers} while {b.name} provides {b.partnership_type or b.offers} into {b.get_country_display()}.",
        "benefits": (ai or {}).get("benefits") or ["New market access", "Existing distribution network", "Reduced partner-discovery costs"],
        "things_to_verify": (ai or {}).get("things_to_verify") or ["Import requirements", "Product certifications", "Pricing", "Distribution terms", "Logistics"],
        "ai": ai is not None,
    }
    return Response(brief)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def match_history(request):
    """Recent matcher searches for the logged-in user (powers search history UI)."""
    qs = MatchQuery.objects.filter(user=request.user).order_by("-created_at")[:20]
    return Response([{"id": q.id, "query": q.query, "result_count": q.result_count,
                      "top_score": q.top_score, "ai_used": q.ai_used,
                      "created_at": q.created_at} for q in qs])


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def metrics(request):
    """Deck slide: 'We measure discovery, match quality, requests, coverage.'"""
    from django.db.models import Avg, Count
    by_status = {r["status"]: r["n"] for r in PartnershipRequest.objects.values("status").annotate(n=Count("id"))}
    searches = MatchQuery.objects.count()
    sent = PartnershipRequest.objects.count()
    return Response({
        "profiles": CapabilityProfile.objects.count(),
        "verified_profiles": CapabilityProfile.objects.filter(is_verified=True).count(),
        "searches": searches,
        "avg_top_score": round(MatchQuery.objects.aggregate(a=Avg("top_score"))["a"] or 0),
        "ai_searches": MatchQuery.objects.filter(ai_used=True).count(),
        "requests_sent": sent,
        "requests_by_status": by_status,
        "request_conversion_pct": round(100 * sent / searches, 1) if searches else 0,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def notifications(request):
    """Activity feed: requests needing you + updates on requests you sent."""
    user = request.user
    items = []
    received = PartnershipRequest.objects.filter(
        to_profile__owner=user, status="pending").order_by("-created_at")[:20]
    for r in received:
        items.append({
            "kind": "request_received", "request_id": r.id,
            "text": f"New {r.partnership_type} request from {r.from_profile.name}",
            "created_at": r.created_at, "status": r.status,
        })
    updated = PartnershipRequest.objects.filter(
        requester=user).exclude(status="pending").order_by("-created_at")[:20]
    for r in updated:
        items.append({
            "kind": f"request_{r.status}", "request_id": r.id,
            "text": f"{r.to_profile.name}: your request was {r.status.replace('_', ' ')}",
            "created_at": r.created_at, "status": r.status,
        })
    # Intent-wall alerts: open broadcasts matching YOUR profiles' country/industry
    from profiles.models import Broadcast
    my_profiles = list(CapabilityProfile.objects.filter(owner=user))
    if my_profiles:
        for b in Broadcast.objects.filter(status="open").exclude(author=user).order_by("-created_at")[:20]:
            intent = detect_intent(b.text)
            for p in my_profiles:
                country_hit = (not b.target_country or p.country == b.target_country) and p.country in intent["countries"]
                industry_hit = (not b.industry or p.industry == b.industry) and p.industry in intent["industries"]
                keyword_hit = bool(set(intent["keywords"]) & tokenize(" ".join([p.offers, p.products_services])))
                if country_hit or industry_hit or keyword_hit:
                    items.append({
                        "kind": "broadcast_match", "request_id": None,
                        "text": f"Intent alert for {p.name}: “{b.text[:90]}”",
                        "created_at": b.created_at, "status": "open",
                    })
                    break
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return Response(items[:30])


class EndorsementSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.ReadOnlyField(source="reviewer.username")

    class Meta:
        model = Endorsement
        fields = ("id", "request", "reviewer", "reviewer_name", "rating", "comment", "created_at")
        read_only_fields = ("id", "reviewer", "created_at")


class EndorsementViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post"]
    serializer_class = EndorsementSerializer

    def get_queryset(self):
        qs = Endorsement.objects.all()
        profile_id = self.request.query_params.get("profile")
        if profile_id:
            qs = qs.filter(Q(request__from_profile_id=profile_id) | Q(request__to_profile_id=profile_id))
        return qs

    def create(self, request):
        from django.db import IntegrityError
        try:
            pr = PartnershipRequest.objects.get(id=request.data.get("request_id"))
        except (PartnershipRequest.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "request_id required"}, status=400)
        if pr.status != "accepted":
            return Response({"detail": "Only accepted partnerships can be endorsed."}, status=400)
        if request.user != pr.requester and request.user != pr.to_profile.owner:
            return Response({"detail": "Only the two partners can endorse."}, status=403)
        try:
            rating = int(request.data.get("rating", 0))
            assert 1 <= rating <= 5
        except (ValueError, TypeError, AssertionError):
            return Response({"detail": "rating must be 1-5"}, status=400)
        if Endorsement.objects.filter(request=pr, reviewer=request.user).exists():
            return Response({"detail": "You already endorsed this partnership."}, status=400)
        try:
            e = Endorsement.objects.create(
                request=pr, reviewer=request.user, rating=rating,
                comment=(request.data.get("comment") or "")[:1000])
        except IntegrityError:
            return Response({"detail": "You already endorsed this partnership."}, status=400)
        return Response(EndorsementSerializer(e).data, status=201)


MOU_TEMPLATE = """# MEMORANDUM OF UNDERSTANDING (DRAFT)

**Between:** {a_name} ({a_country}) — {a_offers}
**And:** {b_name} ({b_country}) — {b_offers}

## Purpose
Explore a {ptype} partnership: {objective}.

## Commitments
- Party A supplies as described above; Party B provides market access and distribution.
- Both parties share necessary certifications and product information.

## Volumes & Terms
- To be agreed in a definitive agreement following due diligence.

## Duration
- 12 months from signature, renewable by mutual consent.

## Dispute Resolution
- Good-faith negotiation first, then mediation under AfCFTA-guided commercial practice.

## Signatures
Party A: ____________________    Party B: ____________________

*Not legally binding — requires independent legal review.*
"""


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_mou(request):
    """Draft MOU for an ACCEPTED request the caller is party to (Gemini, else template)."""
    try:
        pr = PartnershipRequest.objects.get(id=request.data.get("request_id"))
    except (PartnershipRequest.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "request_id required"}, status=400)
    if pr.status != "accepted":
        return Response({"detail": "MOU unlocks once both sides accept."}, status=400)
    if request.user != pr.requester and request.user != pr.to_profile.owner:
        return Response({"detail": "Only the two partners can draft."}, status=403)
    from linka.ai import generate_mou_llm
    a, b = pr.from_profile, pr.to_profile
    md = generate_mou_llm(
        {"name": a.name, "country": a.get_country_display(), "offers": a.offers or a.products_services},
        {"name": b.name, "country": b.get_country_display(), "offers": b.offers or b.products_services},
        pr.partnership_type, pr.message)
    ai_used = md is not None
    if not md:
        md = MOU_TEMPLATE.format(
            a_name=a.name, a_country=a.get_country_display(), a_offers=a.offers or "—",
            b_name=b.name, b_country=b.get_country_display(), b_offers=b.offers or "—",
            ptype=pr.partnership_type, objective=pr.message[:300])
    return Response({"markdown": md, "ai": ai_used})


TRADE_STATIC = {
    "certifications": {
        "Agriculture": ["Phytosanitary certificate", "Food safety cert (e.g. Ghana FDA / NAFDAC for Nigeria)"],
        "Healthcare": ["Marketing authorization from destination health regulator", "GMP certificate"],
        "Manufacturing": ["Certificate of origin (AfCFTA)", "SONCAP-equivalent product conformity"],
    },
    "payments": ["Bank transfer via correspondent banking", "Mobile-money cross-border rails where available",
                 "Escrow for first shipments", "AfCFTA PAPSS settlement where supported"],
}


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def trade_info(request):
    """AfCFTA lane helper: tariffs note, certifications, payment channels (Gemini-enriched)."""
    from linka.ai import generate_trade_llm
    from_country = (request.data.get("from_country") or "").upper()
    to_country = (request.data.get("to_country") or "").upper()
    industry = request.data.get("industry") or "General"
    names = dict(CapabilityProfile.COUNTRIES)
    ai = generate_trade_llm(names.get(from_country, from_country), names.get(to_country, to_country), industry)
    certs = TRADE_STATIC["certifications"].get(industry, ["Certificate of origin (AfCFTA)", "Destination-market product conformity"])
    return Response({
        "lane": f"{names.get(from_country, from_country)} → {names.get(to_country, to_country)}",
        "tariff_note": (ai or {}).get("tariff_note") or
            "Under AfCFTA, qualifying originating goods trade at preferential (often zero) tariffs — confirm the product's rules-of-origin and each country's tariff offer schedule.",
        "certifications": (ai or {}).get("certifications") or certs,
        "payments": (ai or {}).get("payments") or TRADE_STATIC["payments"],
        "ai": ai is not None,
    })


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def voice_intent(request):
    """Voice-note matcher: transcribe audio with Gemini, then run the standard matcher."""
    from django.core.files.uploadedfile import UploadedFile
    from linka.ai import RateLimited, transcribe_audio_llm
    audio: UploadedFile | None = request.FILES.get("audio")
    if not audio:
        return Response({"detail": "audio file required"}, status=400)
    data = audio.read(8 * 1024 * 1024)
    if len(data) < 1024:
        return Response({"detail": "Recording too short — hold the mic and speak for a second or more."}, status=400)
    try:
        transcript = transcribe_audio_llm(data, audio.content_type or "audio/webm")
    except RateLimited:
        return Response({"detail": "Gemini rate limit reached — wait about 30 seconds and try again."}, status=429)
    if not transcript:
        return Response({"detail": "Transcription unavailable (Gemini key/audio needed)."}, status=502)
    llm_intent = cached_llm_intent(transcript)
    intent = llm_intent or detect_intent(transcript)
    qs = CapabilityProfile.objects.all()
    scored = [(s, p, w) for p in qs[:100] for (s, w) in [score_profile(transcript, p, intent)]]
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, profile, reasons in scored[:5]:
        d = CapabilityProfileSerializer(profile).data
        d["match_score"] = score
        d["why"] = reasons
        results.append(d)
    return Response({"transcript": transcript, "intent": intent,
                     "ai": llm_intent is not None, "results": results})
