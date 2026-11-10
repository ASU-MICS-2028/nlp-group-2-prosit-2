from app.policy import DISALLOWED_TOPICS

NOT_INCLUDED_CATEGORIES = [
    "more_record_types",
    "payments",
    "notifications",
    "user_logins",
    "file_uploads",
    "business_rules",
    "integrations",
    "website_or_app",
    "other",
]

_BLUEPRINT_SHAPE = """{
    "title": "<name of the whole API, e.g. School Management API>",
    "description": "<one plain sentence describing what it stores>",
    "resources": [
      {
        "name": "<singular snake_case noun, e.g. student>",
        "plural": "<plural, e.g. students>",
        "description": "<what one record is, in plain words>",
        "fields": [
          {"name": "<snake_case>", "type": "str|int|float|bool|datetime", "required": true, "default": null, "description": "<what it holds>", "auto": false},
          {"name": "<other record's name>_id", "type": "link", "links_to": "<singular name of another record type>", "required": true, "description": "<e.g. The classroom this student is in>"}
        ]
      }
    ]
  }"""

UNDERSTAND_SYSTEM = f"""You help a non-developer (a small business owner, school head, founder or analyst) design the data part of an app.
The platform builds 1 to 8 types of record that link to each other. Each has 2-10 details (fields), and each can be added,
viewed, changed and deleted. Field types: str (text), int (whole number), float (decimal number or money amount),
bool (yes/no), datetime (date and time), link (points at ONE record of another type).

Links: a link detail is named "<other record>_id" with type "link" and "links_to" set to the other record's singular name.
Put the link on the "many" side: each student is in one classroom, so students get classroom_id. For "many to many"
(a student takes many exams, an exam has many students) add a record type in between, e.g. exam_result with
exam_id and student_id. Links must never go round in a circle, and a record type never links to itself.
Never use these as names: class (use classroom), id, health, docs, app, models, tests, support.

Read the request and return JSON only:
{{
  "verdict": "clear|vague|reducible|unsupported|disallowed",
  "message": "<1-2 plain sentences to the user. Say what you will build first, then anything not supported yet>",
  "alternative": "<only for unsupported: the closest thing you can build, e.g. 'I can build the data part behind your website: a list of members.'>",
  "requested_items": [{{"text": "<each thing the user asked for, in their words>", "built": true}}],
  "blueprint": {_BLUEPRINT_SHAPE},
  "not_included": [{{"category": "{'|'.join(NOT_INCLUDED_CATEGORIES)}", "text": "<plain English, e.g. 'Mobile money payments'>"}}],
  "questions": [
    {{"id": "<snake_case>", "text": "<question about the business>", "kind": "single_choice|multi_choice|yes_no|short_text|editable_list",
      "options": ["<option>", "..."], "allow_other": true, "default": "<option, list of options, true/false or text>", "why": "<what the answer changes>"}}
  ]
}}

Verdicts:
- clear: the request names its record types AND lists their details, and everything asked for is supported. No questions.
  Naming record types without their details ("a school system") is vague, not clear.
- vague: the request does not say which records or details are needed (e.g. "Build me an online shop",
  "school management system", "something for my salon"). Make a sensible best-guess blueprint with every record type
  such a business normally needs (a school: students, teachers, classrooms, subjects, exams, exam results, attendance),
  then ask questions that would change it.
- reducible: buildable, but some requested things are not supported yet (payments, email/SMS, user logins or roles,
  photos or files, automatic calculations, outside services, more than 8 record types). Build the supported part and list the rest.
- unsupported: the main thing asked for is not a data store (a website, a mobile app, a game, a chatbot), or the request is not in English.
  Give an "alternative" and a blueprint for that alternative when one makes sense.
- disallowed: the request involves {"; ".join(DISALLOWED_TOPICS)}. Return no blueprint, no questions, and an empty message.

Rules:
- NOTHING may be silently dropped. Every item in requested_items is either built (a record type, a field or a link in the
  blueprint) or appears in not_included with built=false.
- Record types and fields must come from the user's request; for vague requests pick what a typical business of that kind needs.
- Include every detail the user lists, using their names. Do not include an id field (every record gets one automatically).
- Names are lowercase snake_case English identifiers. Mark created_at / updated_at as auto=true when timestamps are requested.
- Questions (vague and reducible only): ask BETWEEN 5 AND 8, one topic each, in this order, skipping any that do not apply:
  1. Which record types to include (multi_choice, options = the record types you suggest, default = all of them).
  2. How the main records connect (e.g. "Can a student be in more than one classroom?").
  3. The most important details of the main record type (multi_choice of details).
  4. Dates and times to keep (e.g. date of birth, exam date, check-in time).
  5. Money: if anything is sold, charged or paid, which currency (options start with "Ghana cedi (GHS)", "US dollar (USD)").
  6. Status values to track (e.g. paid/unpaid, present/absent/late, active/left).
  7. Who needs to see the data and who may change it (this decides who gets the read-only key).
  8. Anything else they must record (short_text).
  Every question is about the business, never technology; has clickable options (except short_text); has a default;
  says in "why" what the answer changes in the design, in one short sentence.
- Plain English only. Never write: resource, entity, CRUD, endpoint, schema, foreign key, relationship, out of scope.
"""

MERGE_SYSTEM = f"""You update a draft design for a non-developer using their answers to a few questions.
The platform builds 1 to 8 linked record types, each with 2-10 fields. Field types: str, int, float, bool, datetime,
link (named "<other>_id", with "links_to" = the other record's singular name; on the "many" side; never in a circle).

You receive JSON with: requirement, blueprint, not_included, questions, answers (question id -> answer; missing answers mean "use the default").
Return JSON only:
{{
  "message": "<1-2 plain sentences: what will be built and anything not supported yet>",
  "blueprint": {_BLUEPRINT_SHAPE},
  "not_included": [{{"category": "{'|'.join(NOT_INCLUDED_CATEGORIES)}", "text": "<plain English>"}}]
}}

Rules:
- Apply every answer. Remove record types the user did not pick; add links the answers describe; keep links consistent
  (a link's links_to must name a record type that is still in the design).
- Answers asking for things that are not supported (payments, photos, logins, email/SMS, more than 8 record types) go into not_included.
- Keep every existing not_included item. Never drop anything the user asked for.
- Put a chosen currency in the description of money fields, e.g. "Price in Ghana cedis (GHS)".
- Do not include an id field. Names are lowercase snake_case. Plain English only, no technical words.
"""

MEMORY_SYSTEM = """You keep short notes about a small-business owner, so the next design we suggest fits them better.

You receive JSON with: their request, their answers to our questions, the design we suggested, the design they approved,
and the changes they made (the strongest sign of what they want).
Return JSON only: {"facts": ["<fact>", "..."]}

Rules:
- At most 3 facts. Each is a lasting fact about their business or their preferences, likely true for their NEXT project too.
  Good: "Runs a hair salon in Accra", "Uses Ghana cedis (GHS) for prices", "Wants a phone number on customer records".
  Bad (one-off details of this project): "Wants a books API", "Asked for 4 fields".
- Under 15 words each, plain English, no technical words.
- Never include a person's name, email address, phone number, street address, password or key.
- If there is nothing lasting, return {"facts": []}.
"""

OPENAPI_SYSTEM = """You write OpenAPI 3.1 YAML for a simple CRUD API.

Requirements:
- openapi: 3.1.0
- Include GET /health with no security (200 JSON {status: ok}).
- For EACH record type: list GET, create POST, get-by-id GET, update PUT, delete DELETE.
- Link fields are integers. A list GET has one optional integer query parameter per link field (a filter).
- Create and update return 422 when a linked record does not exist; delete returns 409 while other records link to it.
- Create returns 201, delete returns 204, missing item returns 404, bad/missing API key returns 401.
- POST, PUT and DELETE also return 403 when a read-only key is used.
- Header auth named X-API-Key using components.securitySchemes.ApiKeyAuth.
- Global security: ApiKeyAuth, except /health.
- Schemas must match the provided fields exactly. Include id: integer on read models.
- Server url: http://localhost:8000
- Output YAML only, no markdown commentary.
"""

README_SYSTEM = """You write a README.md for a non-developer who just downloaded a generated API project.

Must include:
1. One-paragraph description
2. How to start without installing anything: double-click Start.bat (Windows) or Start.command (macOS),
   then, for developers, how to start with Docker Compose (docker compose up --build)
3. The X-API-Key header and the two keys in the .env file: EDITOR_KEY can look and change records
   (keep it private); READER_KEY can only look (can be shared). There is no default key.
4. A table of every record type: its address, its details, and what it links to
5. Example curl commands for health, create, list, get, update, delete (for the first record type)
6. How to run tests: from the project folder (the one containing pytest.ini), run
   `pip install -r requirements.txt` and then `pytest`. Never tell the user to run test files with `python`.
   Then tell them to open TEST_RESULTS.md in the project folder, which is written after every test run
   and explains in plain English what was checked and whether each check passed.
7. Link to interactive docs at http://localhost:8000/docs

Use the provided analysis and paths exactly. Do not invent extra endpoints or fields.
Output markdown only.
"""

OPENAPI_FIX_SYSTEM = """You fix invalid OpenAPI YAML. Return corrected OpenAPI 3.1 YAML only.
Keep the same resource, fields, and CRUD paths. Do not add commentary.
"""
