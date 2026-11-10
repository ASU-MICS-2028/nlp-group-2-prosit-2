"""Fixed, reviewable wording for requests the platform will not build (Phase 2 spec 4.6).

Change this file, not the prompts, to update the policy. The LLM only picks the verdict;
the text users see always comes from here.
"""

DISALLOWED_TOPICS = [
    "collecting or storing people's personal data without their consent",
    "scraping data from websites or social networks",
    "sending spam or bulk unsolicited messages",
    "tracking, monitoring or stalking people",
    "anything illegal",
]

REFUSAL_MESSAGE = (
    "Sorry, I can't help build this. If I misunderstood, please describe what you need in a different way."
)

PLATFORM_SUMMARY = (
    "I build the data part of an app: a place to store records (such as products, customers or "
    "bookings) that you can add, view, change and delete from anywhere."
)

NOT_ENGLISH_MESSAGE = "For now I can only read requests written in English. Please describe what you need in English."
