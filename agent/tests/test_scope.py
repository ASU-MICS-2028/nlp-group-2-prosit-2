"""Tests for the plain check before the AI (agent/scope.py, D-023): websites and collecting people's data."""

import json
from pathlib import Path

import pytest

from agent.scope import check_scope

REQUESTS = json.loads((Path(__file__).parents[2] / "evaluation" / "requests.json").read_text(encoding="utf-8"))
REQUESTS = REQUESTS["requests"] if isinstance(REQUESTS, dict) else REQUESTS


@pytest.mark.parametrize(
    "request_text",
    [
        "Make me a website with a nice homepage and a photo gallery for my church.",  # r19
        "A school website where parents can see news and the term calendar.",
        "Build a restaurant website with our menu and opening hours.",
        "I want a website for my hair salon.",
        "Create a landing page for my new phone shop.",
        "A web page for our football club.",
        "a WEBSITE for my bakery",
    ],
)
def test_a_website_is_refused(request_text):
    refusal = check_scope(request_text)
    assert refusal is not None
    assert refusal.name.endswith("Website") or refusal.name.endswith("Collector")
    assert "API" in refusal.reason  # it says what could be built instead


@pytest.mark.parametrize(
    "request_text",
    [
        "Collect the phone numbers and emails of people from Facebook profiles into a list.",  # r20
        "Scrape names and email addresses from LinkedIn.",
        "Scrape the contact details of every doctor listed on a hospital website.",
        "Crawl online directories and save people's phone numbers and addresses.",
        "Harvest emails from Instagram comments.",
        "Gather names and phone numbers from the internet for my marketing list.",
        "Extract the email addresses from websites about weddings in Accra.",
        "Download the profiles and photos of TikTok users who follow my rival.",
        "A scraper that copies people's Ghana Card numbers from public records.",
        "Pull the personal information of members off a forum.",
    ],
)
def test_collecting_peoples_data_from_any_source_is_refused(request_text):
    refusal = check_scope(request_text)
    assert refusal is not None
    assert refusal.name == "Personal Data Collector"
    assert "consent" in refusal.reason


@pytest.mark.parametrize(
    "request_text",
    [
        "An API for my school website: students, classes and teachers.",  # the person asked for the API
        "The backend for my restaurant website, with menu items and table bookings.",
        "Build me an online shop.",  # r13: a business, built as an API (#54)
        "A bookshop API where customers can find books by name online.",
        "Customers order on my online shop: keep their name, phone and orders.",
        "Keep a list of my church members: full name, phone number and the date they joined.",
        "Track my business expenses: what I spent money on, the amount and the date.",
        "Collect payments from customers: their name, the amount and the date.",
    ],
)
def test_ordinary_requests_go_to_the_ai(request_text):
    assert check_scope(request_text) is None


@pytest.mark.parametrize("item", [r for r in REQUESTS if r["expect"] != "refuse"], ids=lambda r: r["id"])
def test_no_evaluation_request_that_must_be_built_is_refused(item):
    assert check_scope(item["request"]) is None


@pytest.mark.parametrize("item", [r for r in REQUESTS if r["expect"] == "refuse"], ids=lambda r: r["id"])
def test_both_evaluation_requests_that_must_be_refused_are(item):
    assert check_scope(item["request"]) is not None


@pytest.mark.parametrize(
    ("request_text", "name"),
    [
        ("A school website where parents can see news.", "School Website"),
        ("Build a restaurant website with our menu.", "Restaurant Website"),
        ("Make me a website with a nice homepage for my church.", "Church Website"),
        ("I want a website for my hair salon.", "Hair Salon Website"),
        ("A nice website please.", "Website"),
        ("A landing page for my new phone shop.", "Phone Shop Website"),
    ],
)
def test_a_refused_website_gets_a_short_name(request_text, name):
    assert check_scope(request_text).name == name
