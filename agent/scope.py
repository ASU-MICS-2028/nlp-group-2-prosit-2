"""Requests we never build, checked in plain code BEFORE the AI is asked (D-023).

The builder prompt (agent/prompts/builder.md, "Requests you must not build") already tells the AI to refuse these.
But the AI is not the same every time: in a local check it refused "church website" and then started building
"school website" and "restaurant website" as APIs. For the two kinds of request below, a refusal must not depend
on the AI's mood, so this check decides first. It costs no AI request and answers at once.

1. A website: the request asks for a website, web page, homepage or landing page, and does not ask for an API.
   ("An API for my school website" is still built: the person asked for the API.)
2. Collecting people's personal data from somewhere else: scraping or crawling for names, phone numbers, emails,
   addresses, ID numbers and the like, from ANY source (Facebook, LinkedIn, any website, online directories...).

Anything else goes to the AI as before, and the prompt's own rules still apply.
"""

import re
from dataclasses import dataclass


@dataclass
class Refusal:
    name: str  # what was asked, 2-4 words, e.g. "School Website"; the project shows "School Website (not built)"
    reason: str  # one or two plain sentences: why not, and what could be built instead


# re.IGNORECASE: "Website", "WEBSITE" and "website" all match. \b = a word edge, so "websites" matches but "cobweb" doesn't.
WEBSITE = re.compile(r"\b(web ?sites?|web ?pages?|home ?pages?|landing ?pages?)\b", re.IGNORECASE)
ASKS_FOR_AN_API = re.compile(r"\b(apis?|back[- ]?end|endpoints?)\b", re.IGNORECASE)

# Personal data: things that identify a person or let someone reach them.
PERSONAL_DATA = re.compile(
    r"\b(names?|phone|phones|mobile numbers?|e-?mails?|addresses|address|contacts?|contact details|"
    r"birthdays?|dates? of birth|id numbers?|id cards?|national ids?|ghana ?cards?|passports?|"
    r"locations?|photos?|pictures?|profiles?|personal (data|information|details)|pii)\b",
    re.IGNORECASE,
)
# Verbs that only mean taking data from somewhere else: refused with personal data, whatever the source.
SCRAPE = re.compile(r"\b(scrap(e|es|ed|ing|er|ers)|crawl(s|ed|ing|er|ers)?|harvest(s|ed|ing)?|spy(ing)?)\b", re.IGNORECASE)
# Everyday verbs that may also mean taking data: refused only together with personal data AND an outside source.
# ("find", "get" and "track" are left out: "find books by name online" is an ordinary request.)
COLLECT = re.compile(r"\b(collect|gather|extract|copy|pull|grab|mine|mining|download)(s|ed|ing)?\b", re.IGNORECASE)
# A social network named anywhere is an outside source.
SOCIAL = re.compile(
    r"\b(facebook|instagram|linkedin|twitter|x\.com|tiktok|whatsapp|telegram|snapchat|youtube|social media|"
    r"social networks?)\b",
    re.IGNORECASE,
)
# The web counts only as the place the data comes FROM ("from websites", "off the internet"), so
# "customers order on my online shop" is not caught. (?:\w+\s+){0,3} allows up to 3 words in between.
FROM_THE_WEB = re.compile(
    r"\b(from|off|across)\s+(?:\w+\s+){0,3}(web ?sites?|web ?pages?|the web|internet|online|google|directories|"
    r"directory|public records|forums?)\b",
    re.IGNORECASE,
)


# Words that say nothing about what a website is for, so they are left out of its name.
NOT_A_NAME = {"a", "an", "the", "my", "our", "me", "new", "nice", "simple", "small", "own", "good", "beautiful"}


def website_name(request: str) -> str:
    # "a school website" -> "School Website"; "a website for my hair salon" -> "Hair Salon Website"; else "Website".
    before = re.search(r"\b([a-z]+)\s+web ?site\b", request, re.IGNORECASE)  # the word just before "website"
    if before and before.group(1).lower() not in NOT_A_NAME:
        words = [before.group(1)]
    else:
        after = re.search(r"\bfor\s+((?:[a-z]+\s*){1,4})", request, re.IGNORECASE)  # "for my new phone shop"
        words = [w for w in (after.group(1).split() if after else []) if w.lower() not in NOT_A_NAME][:2]
    return " ".join([w.capitalize() for w in words] + ["Website"])


def check_scope(request: str) -> Refusal | None:
    """A Refusal if the request is one we never build (see the module text), otherwise None."""
    personal = PERSONAL_DATA.search(request)
    outside = SOCIAL.search(request) or FROM_THE_WEB.search(request)
    if personal and (SCRAPE.search(request) or (COLLECT.search(request) and outside)):
        return Refusal(
            name="Personal Data Collector",
            reason=(
                "Collecting people's personal details (such as names, phone numbers or emails) from social media, "
                "websites or other sources without their consent is not something we build. An API that keeps "
                "records people give you themselves, such as your own members or customers, can be built instead."
            ),
        )
    if WEBSITE.search(request) and not ASKS_FOR_AN_API.search(request):
        return Refusal(
            name=website_name(request),
            reason=(
                "A website is pages and design, which an API cannot provide. A backend API that keeps the "
                "website's data (for example its members, events, products or bookings) can be built instead: "
                "ask for that API."
            ),
        )
    return None
