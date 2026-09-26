"""Seed demo data for hackathon MVP. Run: python seed_demo.py

Fictional but plausible demo companies across the 5 MVP countries/sectors.
Seed profiles belong to a neutral 'linka_seed' owner so every real account
(including demo) matches against them without matching itself.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "linka.settings")
django.setup()

from django.contrib.auth.models import User
from profiles.models import CapabilityProfile

demo, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@linka.africa"})
demo.set_password("demo12345")
demo.save()

owner, _ = User.objects.get_or_create(username="linka_seed", defaults={"email": "seed@linka.africa"})
owner.set_password("seed12345")
owner.save()

SEED = [
    dict(name="AgroLink Nigeria", country="NG", city="Lagos", industry="Agriculture",
         products_services="Processed cassava products", skills_expertise="Food processing",
         offers="Processed cassava products, food manufacturing capacity",
         needs="Distributor and logistics partner in Ghana",
         partnership_type="Distribution", target_countries=["GH"], is_verified=True),
    dict(name="Kora Distribution Co.", country="GH", city="Accra", industry="Logistics",
         products_services="Nationwide FMCG distribution, cold chain", skills_expertise="Distribution",
         offers="Nationwide FMCG distribution network with cold-chain capacity",
         needs="Food manufacturers seeking Ghana market entry",
         partnership_type="Distribution", target_countries=["NG"], is_verified=True),
    dict(name="Nia Foods & Retail", country="GH", city="Kumasi", industry="Agriculture",
         products_services="Retail network 120+ stores", skills_expertise="Retail",
         offers="Retail shelf space across Accra and Kumasi",
         needs="Processed food suppliers", partnership_type="Retail",
         target_countries=["NG"], is_verified=True),
    dict(name="Mansa Freight", country="GH", city="Tema", industry="Logistics",
         products_services="Cross-border logistics, customs", skills_expertise="Freight, customs",
         offers="Cross-border logistics and customs support for West Africa",
         needs="Manufacturers moving goods NG-GH", partnership_type="Logistics",
         target_countries=["NG", "KE"], is_verified=False),
    dict(name="Nairobi PayTech", country="KE", city="Nairobi", industry="Technology",
         products_services="Mobile payments platform", skills_expertise="Fintech, mobile money",
         offers="Mobile payments infrastructure and API",
         needs="Technology scale-up partners, investors", partnership_type="Technology",
         target_countries=["NG", "RW"], is_verified=True),
    dict(name="Kigali Research Lab", country="RW", city="Kigali", industry="Research",
         products_services="Agri-tech research", skills_expertise="Research, soil science",
         offers="Crop-yield research and pilot programs",
         needs="Manufacturing partners to commercialize research", partnership_type="Research",
         target_countries=["NG", "KE"], is_verified=False),
    dict(name="Ubuntu Packaging", country="ZA", city="Johannesburg", industry="Manufacturing",
         products_services="Sustainable packaging 10k+ units/month", skills_expertise="Manufacturing",
         offers="Sustainable packaging manufacturing capacity",
         needs="B2B buyers across Africa", partnership_type="Manufacturing",
         target_countries=["NG", "GH", "KE"], is_verified=True),
    # --- expansion: more countries x sectors ---
    dict(name="Sahel Grains Board", country="NG", city="Kano", industry="Agriculture",
         products_services="Sorghum and millet aggregation", skills_expertise="Aggregation, storage",
         offers="Bulk grain supply with quality grading",
         needs="Millers and export distributors", partnership_type="Distribution",
         target_countries=["GH", "ZA"], is_verified=False),
    dict(name="Lagos HealthMeds", country="NG", city="Lagos", industry="Healthcare",
         products_services="Pharmaceutical distribution", skills_expertise="Pharma logistics",
         offers="Licensed pharma distribution across Nigeria",
         needs="Pharmaceutical manufacturers in West Africa producing 10,000+ units per month",
         partnership_type="Distribution", target_countries=["GH"], is_verified=True),
    dict(name="Accra Pharma Works", country="GH", city="Accra", industry="Healthcare",
         products_services="Generic drug manufacturing, 50k units/month", skills_expertise="Pharma manufacturing",
         offers="Pharmaceutical manufacturing capacity 50,000 units per month",
         needs="Distributors across West Africa", partnership_type="Manufacturing",
         target_countries=["NG", "KE", "RW"], is_verified=True),
    dict(name="Kumasi Cocoa Processors", country="GH", city="Kumasi", industry="Manufacturing",
         products_services="Cocoa butter and powder", skills_expertise="Agro-processing",
         offers="Cocoa processing capacity for export buyers",
         needs="Cold-chain logistics to Tema port", partnership_type="Manufacturing",
         target_countries=["ZA", "KE"], is_verified=False),
    dict(name="Savanna Solar Kits", country="KE", city="Nairobi", industry="Manufacturing",
         products_services="Pay-as-you-go solar home systems", skills_expertise="Hardware, embedded",
         offers="Solar hardware manufacturing and assembly",
         needs="Distributors in off-grid markets, investors", partnership_type="Manufacturing",
         target_countries=["RW", "NG", "GH"], is_verified=True),
    dict(name="Mombasa Port Runners", country="KE", city="Mombasa", industry="Logistics",
         products_services="Port clearing and last-mile delivery", skills_expertise="Customs, haulage",
         offers="East African port clearing and haulage",
         needs="Manufacturers importing through Mombasa", partnership_type="Logistics",
         target_countries=["RW"], is_verified=False),
    dict(name="Kigali FinServe", country="RW", city="Kigali", industry="Finance",
         products_services="SME trade credit", skills_expertise="Credit scoring, trade finance",
         offers="Working-capital credit for cross-border traders",
         needs="Banking and mobile-money partners", partnership_type="Finance",
         target_countries=["KE", "NG"], is_verified=False),
    dict(name="Cape AgriTech", country="ZA", city="Cape Town", industry="Technology",
         products_services="Farm sensor platform", skills_expertise="IoT, data analytics",
         offers="Precision-farming sensors and analytics API",
         needs="Agribusiness pilots and resellers", partnership_type="Technology",
         target_countries=["KE", "NG", "GH"], is_verified=True),
    dict(name="Jozi Creative Hub", country="ZA", city="Johannesburg", industry="Creative",
         products_services="Design and branding studio", skills_expertise="Branding, packaging design",
         offers="Brand and packaging design for export products",
         needs="Manufacturers needing export-ready branding", partnership_type="Creative",
         target_countries=["NG", "GH"], is_verified=False),
    dict(name="Nairobi EdTech College", country="KE", city="Nairobi", industry="Education",
         products_services="Logistics and tech vocational courses", skills_expertise="Training, certification",
         offers="Certified talent pipeline in logistics and tech",
         needs="Employers and internship partners", partnership_type="Education",
         target_countries=["RW", "GH"], is_verified=False),
    dict(name="Cairo MedSupply", country="EG", city="Cairo", industry="Healthcare",
         products_services="Medical devices import", skills_expertise="Procurement, regulation",
         offers="Sourcing channel for affordable medical devices",
         needs="Sub-Saharan distribution partners", partnership_type="Distribution",
         target_countries=["KE", "NG", "ZA"], is_verified=False),
]

for s in SEED:
    CapabilityProfile.objects.update_or_create(name=s["name"], defaults={**s, "owner": owner})

from profiles.models import Milestone

TIMELINE = [
    ("Kora Distribution Co.", "shipment", "Dispatched 10 tons of processed goods Lagos → Tema", "Cross-border FMCG run completed without delays.", True),
    ("Kora Distribution Co.", "milestone", "Cold-chain capacity expanded by 30%", "New refrigerated units commissioned in Accra depot.", False),
    ("Accra Pharma Works", "certification", "Renewed GMP certification for 2026", "Good Manufacturing Practice audit passed.", True),
    ("Ubuntu Packaging", "shipment", "Delivered 25,000 sustainable units to Nairobi buyer", "Repeat order confirmed for next quarter.", True),
    ("Nairobi PayTech", "partnership", "API integration with regional mobile-money rail", "Live in Kenya and Rwanda.", False),
]
for name, kind, title, detail, verified in TIMELINE:
    p = CapabilityProfile.objects.filter(name=name).first()
    if p:
        Milestone.objects.get_or_create(profile=p, title=title, defaults={"kind": kind, "detail": detail, "is_verified": verified})

print(f"Seeded {CapabilityProfile.objects.count()} profiles (demo login: demo / demo12345)")
