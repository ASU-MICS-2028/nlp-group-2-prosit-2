"""Step 5: measure retrieval on its own, without any LLM (free, repeatable).

Each query is a request written in DIFFERENT words from the seed examples, with the seed it should find.
"Top-1" means the right example came first; "top-3" means it was among the 3 given to the model.

    .venv\\Scripts\\python -m app.rag_check
"""

from __future__ import annotations

from app.config import settings
from app.retrieval import embedding_model, search, search_by_meaning, seed_examples

# (a new request, the seed title it should match)
QUERIES: list[tuple[str, str]] = [
    ("appointments for my barbershop and beauty parlour customers", "Salon Bookings API"),
    ("I sell clothes online and need my items, prices and stock", "Products API"),
    ("register of people in our congregation", "Church Members API"),
    ("a hospital wants to book patients to see a doctor", "Clinic Appointments API"),
    ("customers ordering tomatoes and yams from my farm for delivery", "Produce Orders API"),
    ("my library of novels with the writer of each one", "Bookshop API"),
    ("pupils and their classes at our basic school", "Students API"),
    ("money my company spent this month", "Expenses API"),
    ("hotel rooms and nightly rates", "Guest House Rooms API"),
    ("concerts and shows with ticket counts", "Events API"),
    ("okada riders who deliver for my business", "Riders API"),
    ("the dishes and meals my chop bar serves", "Menu API"),
    ("fitness centre memberships and when they expire", "Gym Members API"),
    ("fixing broken phones for customers", "Phone Repairs API"),
    ("gifts of money from supporters of our charity", "Donations API"),
    ("renting out vehicles by the day", "Car Rental API"),
    ("to-do items for my staff with deadlines", "Tasks API"),
    ("candidates applying for jobs and their interviews", "Applicants API"),
    ("drugs in my chemist shop and when they expire", "Pharmacy Stock API"),
    ("dresses and kaba outfits customers ordered from my seamstress shop", "Tailoring Orders API"),
    ("a system for our basic school: pupils, staff, class registers and term exams", "School Management API"),
]

# Requests unlike every seed: nothing should be given to the model for these
UNRELATED: list[str] = [
    "write me a poem about the sea",
    "what is the weather tomorrow",
    "translate hello into Twi",
]

# HELD-OUT set, written on 2026-11-04 BEFORE trying any retrieval improvement. Never use it to choose
# settings (the cut-off is chosen on QUERIES above); it only measures how well a choice generalises.
HELD_OUT: list[tuple[str, str]] = [
    ("my beauty salon needs a booking diary for hair and nails", "Salon Bookings API"),
    ("stock and prices for my provisions shop", "Products API"),
    ("keep the list of our church members and when they joined", "Church Members API"),
    ("patients seeing the nurse or doctor at our health centre", "Clinic Appointments API"),
    ("buyers who order maize and cassava from my farm", "Produce Orders API"),
    ("a catalogue of textbooks and storybooks I sell", "Bookshop API"),
    ("register of children in each class at my primary school", "Students API"),
    ("track what the business spends on fuel and rent", "Expenses API"),
    ("bedrooms at my lodge, their rates and if they are booked", "Guest House Rooms API"),
    ("a list of upcoming programmes and how many seats remain", "Events API"),
    ("dispatch riders and their motorbikes", "Riders API"),
    ("food on our restaurant menu and the prices", "Menu API"),
    ("people who pay monthly at my fitness gym", "Gym Members API"),
    ("laptops and phones customers bring in for fixing", "Phone Repairs API"),
    ("money people give to our foundation", "Donations API"),
    ("cars my company hires out to customers", "Car Rental API"),
    ("jobs the team must finish and their due dates", "Tasks API"),
    ("people who applied to work here and their interview times", "Applicants API"),
    ("medicines on the shelf and their expiry dates", "Pharmacy Stock API"),
    ("clothes people ordered from my tailor shop", "Tailoring Orders API"),
    ("run my school: pupils, teachers, classes, exams and who attended", "School Management API"),
]
HELD_OUT_UNRELATED: list[str] = [
    "tell me a joke",
    "how do I cook jollof rice",
    "who won the football match yesterday",
    "convert 100 dollars to cedis",
    "summarise this news article for me",
]


def _searcher(method: str):
    """The search function and cut-off for one method, exactly as the builder uses them."""
    if method == "embedding":
        return search_by_meaning, settings.rag_embedding_min_score
    return search, settings.rag_min_score


def evaluate(method: str = "tfidf", held_out: bool = False) -> dict:
    """Score one method on the tuning set (default) or the held-out set."""
    find, cut = _searcher(method)
    examples = list(seed_examples())
    queries, unrelated_queries = (HELD_OUT, HELD_OUT_UNRELATED) if held_out else (QUERIES, UNRELATED)
    rows = []
    for query, expected in queries:
        results = find(query, examples, 3, cut)
        titles = [example.title for example, _ in results]
        best = results[0][1] if results else 0.0
        rows.append({"query": query, "expected": expected, "got": titles, "best_score": round(best, 3),
                     "top1": bool(titles) and titles[0] == expected, "top3": expected in titles})
    unrelated = {query: [e.title for e, _ in find(query, examples, 3, cut)] for query in unrelated_queries}
    return {
        "method": method,
        "cut": cut,
        "rows": rows,
        "top1": sum(row["top1"] for row in rows),
        "top3": sum(row["top3"] for row in rows),
        "wrong": sum(1 for row in rows if row["got"] and not row["top1"]),
        "total": len(rows),
        "unrelated": unrelated,
    }


def _report(result: dict, label: str) -> None:
    print()
    print(f"{result['method'].upper()} on the {label} set ({result['total']} requests, min score {result['cut']}):")
    for row in result["rows"]:
        mark = "OK  " if row["top1"] else ("top3" if row["top3"] else ("WRONG" if row["got"] else "MISS"))
        print(f"  [{mark}] {row['best_score']:.3f}  {row['query']!r} -> {row['got'][:1] or ['(nothing)']}  (want {row['expected']})")
    matched = sum(bool(titles) for titles in result["unrelated"].values())
    print(f"  Right first: {result['top1']} of {result['total']}   Wrong first: {result['wrong']}   "
          f"Unrelated matched: {matched} of {len(result['unrelated'])}")
    for query, titles in result["unrelated"].items():
        if titles:
            print(f"    unrelated {query!r} -> {titles[0]}")


def main() -> None:
    methods = ["tfidf"] + (["embedding"] if embedding_model() is not None else [])
    for method in methods:
        _report(evaluate(method), "TUNING")
        _report(evaluate(method, held_out=True), "HELD-OUT")
    if "embedding" not in methods:
        print()
        print("(The embedding model is not installed, so only TF-IDF was measured.)")


if __name__ == "__main__":
    main()
