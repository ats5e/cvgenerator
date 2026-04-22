"""
ai_engine.py
AI-powered tailoring engine for DT's CV & Cover Letter Generator.
Calls OpenAI gpt-4o to analyse a job description and produce a fully
tailored config dict for generator.py and cover_letter_generator.py.
"""
from __future__ import annotations

import json
import os
import re

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

_API_TIMEOUT = 90  # seconds for every OpenAI call

# ---------------------------------------------------------------------------
# Candidate background — the model's only source of truth about DT.
# Written to be maximally useful to a CV writer: scope, context, specifics.
# ---------------------------------------------------------------------------
CANDIDATE_CONTEXT = """
CANDIDATE: Du-Toit Griesel
Location: Dubai, United Arab Emirates
Contact: +971 52 845 5283 | dutoitgriesel@gmail.com | linkedin.com/in/dutoitgriesel
Nationality: South African | Languages: English (native), Afrikaans (native)

CAREER NARRATIVE:
Du-Toit is a senior agency professional with 8+ years of experience running integrated
client accounts and multi-channel brand campaigns across Dubai and South Africa. His career
spans some of the region's most respected agency brands — Yellow, VMLY&R, Ogilvy — giving
him a strong mix of strategic client counsel, hands-on campaign execution, and cross-
functional team leadership. He is currently based in Dubai and is seeking senior roles in
marketing, brand management, or client leadership across the GCC and MENA region.

CAREER TIMELINE:

1. Senior Account Manager — Yellow Branding & Digital Consultancy, Dubai (Oct 2025 – Present)
   SCOPE: Senior lead on multiple integrated client accounts; full ownership of scope,
   budgets, timelines, and delivery quality across branding, digital and campaign briefs.
   KEY ACTIVITIES:
   - Leads senior client relationships with C-suite and marketing director stakeholders
   - Manages integrated delivery across strategy, creative, design, production and digital
   - Runs status reporting, issue escalation, budget tracking and approval workflows
   - Oversees campaign rollout from brief through production, launch and post-campaign review
   STRENGTHS THIS ROLE SHOWS: Senior stakeholder management, integrated campaign leadership,
   budget governance, cross-functional coordination, client retention.

2. Account Manager — Yellow Branding & Digital Consultancy, Dubai (Sep 2023 – Oct 2025)
   SCOPE: Day-to-day account lead on multi-channel brand and digital rollout projects in UAE.
   KEY ACTIVITIES:
   - Managed brand identity, digital rollout and integrated campaign briefs for UAE clients
   - Coordinated strategy, creative, design and production teams to meet fast-turn deadlines
   - Wrote and interrogated creative briefs; aligned teams and protected scope through delivery
   - Built client trust through structured communication, clear status updates and follow-through
   STRENGTHS THIS ROLE SHOWS: Brief writing, multi-channel campaign delivery, agency
   coordination, scope management, UAE market knowledge.

3. Account Manager — HAASXSWITCH (Haas Advertising x Switch Design), Cape Town (Mar 2022 – Sep 2023)
   SCOPE: Client lead on new brand launches and integrated campaigns post-agency merger.
   KEY ACTIVITIES:
   - Project-managed new brand launches across identity, print, digital and retail touchpoints
   - Ran integrated campaigns spanning traditional media, digital, activations and in-store
   - Acted as day-to-day client lead across design, copy, production and strategy workstreams
   - Coordinated delivery across multiple concurrent projects and tight commercial timelines
   STRENGTHS THIS ROLE SHOWS: Brand launch management, integrated campaign execution,
   retail and in-store marketing, multi-workstream coordination.

4. Account Manager — VMLY&R (formerly Geometry Global), Cape Town (May 2020 – Dec 2021)
   SCOPE: Account lead on British American Tobacco campaigns during COVID-19.
   KEY ACTIVITIES:
   - Managed complex regulatory-environment campaigns with strict compliance requirements
   - Coordinated remote approvals, production and delivery under operational constraints
   - Maintained output quality and client trust through highly structured processes
   STRENGTHS THIS ROLE SHOWS: Regulated-industry campaigns, remote team management,
   approval workflows, quality control under pressure.

5. Senior Account Executive — Ogilvy & Mather, Cape Town (Jul 2018 – May 2020)
   SCOPE: Supported senior teams on retail and integrated client accounts.
   KEY ACTIVITIES:
   - Ran retail and integrated projects from brief through final production
   - Recognised by senior leadership for ownership and independence
   - Built strong client relationships on demanding accounts
   STRENGTHS THIS ROLE SHOWS: Retail marketing, project ownership, client handling,
   integrated production.

6. Account Executive — Shift ONE Advertising Agency, Cape Town (Nov 2017 – Jul 2018)
   SCOPE: Junior account role in a digital-led agency.
   KEY ACTIVITIES: Estimates, trafficking, QA, production coordination, client communication.

EDUCATION:
- Bachelor's Degree, Integrated Marketing Communication — AAA School of Advertising (2014–2016)
  Specialisations: Account Management, Brand Management, Digital Media Marketing.
- Certificate in Copywriting for a Digital World — AAA School of Advertising

HARD FACTS TO USE:
- 8+ years of agency experience across UAE and South Africa
- Experience in Dubai, UAE market since September 2023
- Senior-level stakeholder access (CMO, Marketing Director, Brand Manager level)
- Agency roster includes Yellow (Dubai), VMLY&R, Ogilvy, HAASXSWITCH
- Sectors touched: FMCG, F&B, retail, digital, branding, government/public sector (UAE)
- NO fabricated metrics — use scope, scale and context instead of invented numbers
"""

# ---------------------------------------------------------------------------
# System prompt — the model's operating instructions
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a world-class CV writer, career strategist, and ATS optimisation expert.
Your output will be printed verbatim in a PDF sent to a real hiring manager at a real company.
It must be better than anything the candidate could write themselves.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW ATS SYSTEMS SCORE A CV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Exact phrase matching — "brand P&L" scores more than "budget"
2. Keyword distribution — a phrase that appears in summary + skills + a bullet scores 3× vs once
3. Semantic relevance — the AI parser checks if your document discusses the same topics as the JD
4. Section presence — Summary, Skills, Experience, Education must all be populated
5. Keyword density — 12–18 key phrases woven naturally across the document is the target

ATS STRATEGY: Extract the 12–18 most important multi-word phrases from the JD.
Place the top 6–8 across at least two sections each (summary + skills, or skills + bullets).
The rest appear once. Prioritise exact JD phrasing over synonyms.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW HIRING MANAGERS EVALUATE IN 30 SECONDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Title match — does this person hold a comparable title?
2. Company signal — is the current employer credible for this role?
3. Summary — is this written for me, or is it a generic template?
4. Skills — does this list reflect exactly what I asked for?
5. Top 2 bullets of current role — can they do the specific work I need?

The summary and top two bullets of the current role are the most important fields.
Write them last, when you know exactly what the JD demands.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CV BULLET RULES — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TENSE: Role 0 (current) = present tense. Roles 1, 2, 3 = past tense. No exceptions.

ACTION VERBS: Start every bullet with a strong, specific action verb.
  ✗ Never: "Responsible for", "Worked on", "Helped with", "Involved in"
  ✓ Always: Lead, Drive, Manage, Coordinate, Oversee, Develop, Execute, Deliver, Direct

VOCABULARY MIRRORING: Use the JD's exact phrasing inside bullets.
  If the JD says "A&P budget" → bullet says "A&P budget" (not "marketing spend")
  If the JD says "shopper marketing" → bullet says "shopper marketing"
  If the JD says "GCC markets" → bullet mentions GCC or specific GCC countries

STRUCTURE: Keep bullets under 22 words. Use this skeleton:
  [Strong verb] [what you did] [using what / where] [to what end / with what result]

ANTI-PATTERNS — these make CVs look weak and generic:
  ✗ "ensuring alignment with strategic objectives"
  ✗ "with a focus on delivering results"
  ✗ "in order to achieve business goals"
  ✗ "managing multiple stakeholders effectively"
  ✗ "driving business growth"
  ✗ Ending bullets with "...for the business" or "...for the team"

EXAMPLE — for a Brand Manager / FMCG JD:
  ✗ WEAK: "Led integrated client accounts, managing scope, timelines, and budgets."
  ✓ STRONG: "Lead 360 FMCG brand campaigns across UAE, managing A&P budgets, agency
             partners, and shopper marketing activations from brief through launch."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILLS RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 10 items, ordered by prominence in the JD (most critical first)
- 1–4 words each — professional competency headings, not sentences
- Use the JD's preferred terms: if it says "shopper marketing", use "Shopper Marketing"
- ✗ Never: "Proven experience managing...", "Strong understanding of...", "Ability to..."
- ✗ Never: Degree, language, or eligibility requirements
- ✓ Good: "Brand Strategy", "Integrated Campaign Management", "Shopper Marketing"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Two sentences, third-person implied (no "I")
- Sentence 1: [Role title from JD] with [X years] of experience in [top 2 JD themes].
- Sentence 2: Strongest relevant proof + positioning statement for this specific role.
- If the JD names a sector or category (FMCG, luxury, tech, F&B), name it in sentence 1.
- Embed 3–4 high-priority ATS keywords naturally across both sentences.
- ✗ Never: "Proven track record", "Proven ability", "results-driven", "dynamic", "seasoned"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVER LETTER RULES — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Voice: First person singular only (I, me, my). Never "Du-Toit", "he", "him", "his".

BANNED OPENERS — these get CVs binned immediately:
  ✗ "I am thrilled / excited / delighted / pleased to apply"
  ✗ "I am writing to apply for / express my interest in"
  ✗ "I am reaching out regarding"
  ✗ Any sentence starting with "I am [emotion]"

BANNED PHRASES anywhere in the letter:
  ✗ "resonates with my …" / "resonates with my professional values" — always hollow
  ✗ "passion for" / "passionate about"
  ✗ "I am eager to bring my skills"
  ✗ "I believe I would be a great asset"
  ✗ "perfect fit" / "dream role"
  ✗ "proven track record" — cliché, replace with a specific claim
  ✗ "I look forward to hearing from you soon"
  ✗ "Thank you for your time and consideration" as a standalone sentence

PARAGRAPH STRUCTURE:
  P1 (2–3 sentences): Lead with your seniority + the role + the single clearest reason you belong.
     Open like a confident peer, not a job seeker. Example structure:
     "With [X] years of [relevant experience], I bring [specific thing this role needs]
      directly to [company name]'s [team/challenge]."

  P2 (2–3 sentences): Your most relevant real experience mapped to 2–3 specific JD requirements.
     Name real deliverables, real markets, real contexts. No vague claims.

  P3 (2–3 sentences): Something specific about THIS company or role that genuinely connects
     to your work — not "your values", not "your culture" — something real from the JD:
     the category, the scale, the challenge, the market.

  P4 (1–2 sentences): A direct, confident close. Invite a conversation. No "enthusiasm".
     Example: "I would welcome the opportunity to discuss how my background in [X] can
     support [company]'s [specific goal]. Thank you for considering my application."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GUARDRAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- DO NOT INVENT: No fabricated metrics, job titles, tools, degrees, or achievements
- NO KEYWORD STUFFING: every keyword must be embedded in a natural sentence
- STAY GROUNDED: every claim must be traceable to the candidate context above
- The output will be read by a human. Every sentence must earn its place.

Return ONLY valid JSON matching the schema. No markdown fences. No explanation."""


# ---------------------------------------------------------------------------
# JSON schema — defines every field the model must produce
# ---------------------------------------------------------------------------
JSON_SCHEMA = """{
  "company_name": "string — hiring company name from the JD (not a recruiter)",
  "target_role": "string — exact role title as it appears in the JD",
  "role_badge": "string — role title in ALL CAPS, max 4 words, e.g. 'SENIOR BRAND MANAGER'",
  "tagline": "string — exactly three keyword phrases separated by ' | ', using JD vocabulary. E.g. 'Brand Strategy | GCC Market Execution | Stakeholder Engagement'",
  "summary": "string — two sentences, third-person implied (no I). Sentence 1 opens with the JD role title and names the sector if given. Sentence 2 states the strongest positioning proof and closes with a full stop. Total under 60 words.",
  "skills": [
    "exactly 10 items — 1-4 word professional competency headings ordered by JD priority.",
    "Use the JD's exact terminology.",
    "No sentences, no requirements, no language/degree items."
  ],
  "experience_overrides": {
    "0": ["Present-tense bullet 1 for current Yellow SAM role (≤22 words, strong verb, JD vocabulary)", "Present-tense bullet 2 (≤22 words)"],
    "1": ["Past-tense bullet 1 for Yellow AM role (≤22 words)", "Past-tense bullet 2 (≤22 words)"],
    "2": ["Past-tense bullet 1 for HAASXSWITCH AM role (≤22 words, only include if this role is meaningfully relevant to the JD)", "Past-tense bullet 2 (≤22 words)"]
  },
  "ats_keywords": ["12-18 exact multi-word phrases extracted verbatim from the JD, ordered by importance"],
  "cover_letter_recipient": "string — e.g. 'Dear [Company] Hiring Team,'",
  "cover_letter_focus": "string — 3-5 word angle, e.g. 'FMCG Brand Leadership, GCC'",
  "cover_letter_paragraphs": [
    "Para 1 (2-3 sentences): Confident opening — seniority + role + clearest fit credential. No banned openers.",
    "Para 2 (2-3 sentences): Specific real experience mapped to 2-3 JD requirements. Name real places, deliverables, contexts.",
    "Para 3 (2-3 sentences): Something specific and real about this company/role from the JD. Not values or culture — the category, scale, or challenge.",
    "Para 4 (1-2 sentences): Direct confident close. Invite a conversation. No banned phrases."
  ]
}"""


# ---------------------------------------------------------------------------
# User prompt — the per-request instruction with the actual JD
# ---------------------------------------------------------------------------
USER_PROMPT_TEMPLATE = """Produce a tailored CV config and cover letter for Du-Toit Griesel for the job description below.

{candidate_context}

━━━ JOB DESCRIPTION ━━━
{job_description}
━━━ END JD ━━━

ANALYSIS STEPS — work through these before writing anything:

1. ROLE DECODE: What is the exact title, seniority level, and primary function of this role?
   What does success look like in the first 6 months?

2. TOP REQUIREMENTS: What are the 5-7 things the hiring manager most needs to see evidence of?
   List them in priority order.

3. VOCABULARY MAP: What specific terms, tools, markets, or metrics does the JD use that must
   appear verbatim in the CV? (e.g. "A&P budget", "GCC markets", "360 campaigns")

4. CANDIDATE FIT: Which 3-4 elements of DT's background best prove fit for this role?
   What is the strongest angle to lead with?

5. GAPS: Is there anything in the JD that DT cannot credibly claim? Do not fabricate it —
   simply do not surface it, or reframe what he can credibly claim.

Now produce the JSON output matching this schema:
{schema}

FINAL CHECKLIST before submitting:
✓ Role 0 bullets use present tense throughout (Lead, Manage, Drive)
✓ Roles 1 and 2 bullets use past tense (Led, Managed, Drove)
✓ Every bullet contains at least one phrase from the JD vocabulary map
✓ No bullet contains: "ensuring alignment", "with a focus on", "in order to", "managing to"
✓ Summary names the sector/industry if the JD specifies one
✓ Skills list uses JD terminology, not generic synonyms
✓ Cover letter P1 does NOT start with "I am thrilled/excited/delighted/writing to apply"
✓ Cover letter P3 references something specific from the JD (not "values" or "culture")
✓ Cover letter contains no: "resonates with my professional values", "passion for", "eager to bring"
✓ All four cover letter paragraphs are in first person singular (I/me/my)"""


# ---------------------------------------------------------------------------
# Quality-gate patterns
# ---------------------------------------------------------------------------

# Cover letter — first-person check
_FIRST_PERSON_RE = re.compile(
    r"\b(i|i'm|i'd|i've|i'll|me|my|mine|myself)\b", flags=re.IGNORECASE
)
_THIRD_PERSON_RE = re.compile(
    r"\b(du-toit|dt|he|him|his)\b", flags=re.IGNORECASE
)

# Cover letter — banned phrases that signal generic / junior output
_BANNED_CL_RE = re.compile(
    r"i am (thrilled|excited|delighted|pleased|happy|writing to apply|reaching out)|"
    r"resonates? with my|"  # catches "resonates with my values/expertise/etc" — always sounds hollow
    r"passion for|passionate about|"
    r"i am eager to bring|"
    r"perfect fit|dream role|"
    r"i believe i (would be|will be) a great asset|"
    r"proven track record|"
    r"thank you for your time and consideration$",
    flags=re.IGNORECASE,
)

# Skills — patterns that indicate JD copy-paste or requirement language
_BAD_SKILL_RE = re.compile(
    r"\b("
    r"bachelor|degree|required|preferred|must|plus|proficiency|english|languages|"
    r"track record|proven experience|strong understanding|adept at|ability to|"
    r"experience managing|managing multiple|presenting concepts|award-winning|"
    r"years of experience|demonstrated"
    r")\b",
    flags=re.IGNORECASE,
)

# Experience bullets — weak / filler patterns
_WEAK_BULLET_RE = re.compile(
    r"ensuring alignment|"
    r"with a focus on|"
    r"in order to|"
    r"managing to|"
    r"\bfor the (business|team|company|organisation|organization)\b|"
    r"\bdriving (business |overall )?growth\b|"
    r"\bresponsible for\b|"
    r"\bworked (on|with|alongside)\b|"
    r"\binvolved in\b",
    flags=re.IGNORECASE,
)


def _normalise_quotes(text: str) -> str:
    return text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')


# ---------------------------------------------------------------------------
# Quality-gate functions — each returns True if a fix pass is needed
# ---------------------------------------------------------------------------

def _cover_letter_needs_first_person_fix(paragraphs: list[str]) -> bool:
    combined = _normalise_quotes(" ".join(p.strip() for p in paragraphs if str(p).strip()))
    if not combined:
        return False
    fp = len(_FIRST_PERSON_RE.findall(combined))
    tp = len(_THIRD_PERSON_RE.findall(combined))
    return fp == 0 or tp > fp


def _cover_letter_has_banned_phrases(paragraphs: list[str]) -> bool:
    combined = _normalise_quotes(" ".join(p.strip() for p in paragraphs if str(p).strip()))
    return bool(_BANNED_CL_RE.search(combined))


def _skills_need_polish(skills: list[str]) -> bool:
    cleaned = [str(s).strip() for s in skills if str(s).strip()]
    if len(cleaned) != 10:
        return True
    for skill in cleaned:
        words = re.findall(r"[A-Za-z0-9&/+\-']+", skill)
        if not words or len(words) > 6:
            return True
        if any(ch in skill for ch in (",", ";", ":")):
            return True
        if _BAD_SKILL_RE.search(skill):
            return True
    return False


def _bullets_need_improvement(experience_overrides: dict) -> bool:
    all_bullets = []
    for bullets in experience_overrides.values():
        all_bullets.extend(str(b) for b in bullets if str(b).strip())
    if not all_bullets:
        return False
    combined = " ".join(all_bullets)
    return bool(_WEAK_BULLET_RE.search(combined))


# ---------------------------------------------------------------------------
# Targeted fix passes — each fires only when its quality gate fails
# ---------------------------------------------------------------------------

def _fix_skills(client: OpenAI, company: str, role: str, jd: str, skills: list[str]) -> list[str]:
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.15,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Rewrite this CV skills list for Du-Toit Griesel. "
                    "Return exactly 10 items. Each must be a 1-4 word professional competency "
                    "heading grounded in his real agency experience and ordered by relevance to "
                    "the job description. Use the JD's exact terminology. No sentences, no "
                    "requirements, no language or degree items."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    f"JOB DESCRIPTION:\n{jd.strip()}\n\n"
                    f"CURRENT SKILLS (needs fixing):\n{json.dumps(skills, ensure_ascii=False)}\n\n"
                    f"Return only JSON: {{\"skills\":[...10 items...]}}"
                ),
            },
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    result = [str(s).strip() for s in json.loads(raw).get("skills", []) if str(s).strip()]
    return result if len(result) == 10 else skills


def _fix_bullets(client: OpenAI, company: str, role: str, jd: str, overrides: dict) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Rewrite these CV experience bullets for Du-Toit Griesel. "
                    "Rules: role 0 uses present tense (Lead/Manage/Drive); roles 1 and 2 use past tense. "
                    "Every bullet must start with a strong action verb. "
                    "Every bullet must contain at least one specific phrase from the job description. "
                    "No filler phrases: no 'ensuring alignment', 'with a focus on', 'in order to', "
                    "'responsible for', 'worked on'. Under 22 words each. "
                    "Stay grounded in real experience — do not invent metrics or achievements."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    f"JOB DESCRIPTION:\n{jd.strip()}\n\n"
                    f"CURRENT BULLETS (need fixing):\n{json.dumps(overrides, ensure_ascii=False)}\n\n"
                    "Rewrite to be punchy, JD-specific, and tense-correct. "
                    "Return JSON: {\"experience_overrides\": {\"0\": [...], \"1\": [...], \"2\": [...]}}"
                ),
            },
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    data = json.loads(raw)
    fixed = {}
    for k, v in data.get("experience_overrides", {}).items():
        bullets = [str(b).strip() for b in v if str(b).strip()]
        if bullets:
            fixed[k] = bullets
    return fixed if fixed else overrides


def _fix_cover_letter(
    client: OpenAI,
    company: str,
    role: str,
    jd: str,
    focus: str,
    paragraphs: list[str],
    fix_voice: bool,
    fix_phrases: bool,
) -> tuple[str, list[str]]:
    issues = []
    if fix_voice:
        issues.append("rewrite into first-person singular (I/me/my) — never refer to the candidate by name or as he/him/his")
    if fix_phrases:
        issues.append(
            "remove ALL banned phrases: 'thrilled/excited/delighted to apply', "
            "'resonates with my [anything]', 'passion for', 'eager to bring my skills', "
            "'I believe I would be a great asset', 'proven track record'. "
            "Replace with confident, specific, peer-level language."
        )

    issue_text = " AND ".join(issues) if issues else "polish into the strongest possible version"

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.25,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are rewriting a cover letter for Du-Toit Griesel. "
                    "Keep exactly four paragraphs in the same order. "
                    "Write in first-person singular (I/me/my). "
                    "Never refer to the candidate by name or as he/him/his. "
                    "P1: Confident opening — no 'thrilled/excited to apply'. "
                    "P2: Specific real experience, named deliverables and markets. "
                    "P3: Something specific from the JD — the category, challenge, or scale. "
                    "P4: Direct close, two sentences max. "
                    "Maintain professional confidence throughout. "
                    "Do not invent metrics or achievements."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    f"JOB DESCRIPTION:\n{jd.strip()}\n\n"
                    f"CURRENT PARAGRAPHS:\n{json.dumps(paragraphs, ensure_ascii=False)}\n\n"
                    f"ISSUES TO FIX: {issue_text}\n\n"
                    "Return JSON: {\"cover_letter_focus\": \"...\", \"cover_letter_paragraphs\": [\"p1\",\"p2\",\"p3\",\"p4\"]}"
                ),
            },
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    data = json.loads(raw)
    new_focus = str(data.get("cover_letter_focus", focus or "")).strip()
    new_paras = [str(p).strip() for p in data.get("cover_letter_paragraphs", []) if str(p).strip()]
    if len(new_paras) == 4:
        return new_focus or focus, new_paras
    return focus, paragraphs


# ---------------------------------------------------------------------------
# Main LLM call
# ---------------------------------------------------------------------------

def _call_llm(job_description: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Check your .env file.")

    client = OpenAI(api_key=api_key)

    user_message = USER_PROMPT_TEMPLATE.format(
        candidate_context=CANDIDATE_CONTEXT,
        job_description=job_description.strip(),
        schema=JSON_SCHEMA,
    )

    # ── Primary generation call ───────────────────────────────────────────
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    data = json.loads(raw)

    company = data.get("company_name", "Company")
    role = data.get("target_role", "Role")

    # ── Skills quality gate ───────────────────────────────────────────────
    skills = [str(s).strip() for s in data.get("skills", []) if str(s).strip()]
    if skills and _skills_need_polish(skills):
        try:
            data["skills"] = _fix_skills(client, company, role, job_description, skills)
        except Exception:  # noqa: BLE001
            pass

    # ── Experience bullets quality gate ──────────────────────────────────
    raw_overrides = data.get("experience_overrides", {})
    if raw_overrides and _bullets_need_improvement(raw_overrides):
        try:
            fixed = _fix_bullets(client, company, role, job_description, raw_overrides)
            if fixed:
                data["experience_overrides"] = fixed
        except Exception:  # noqa: BLE001
            pass

    # ── Cover letter quality gates (single conditional pass) ─────────────
    paragraphs = [str(p).strip() for p in data.get("cover_letter_paragraphs", []) if str(p).strip()]
    focus = str(data.get("cover_letter_focus", "")).strip()
    needs_voice_fix = _cover_letter_needs_first_person_fix(paragraphs)
    needs_phrase_fix = _cover_letter_has_banned_phrases(paragraphs)

    if paragraphs and (needs_voice_fix or needs_phrase_fix):
        try:
            new_focus, new_paras = _fix_cover_letter(
                client, company, role, job_description, focus,
                paragraphs, needs_voice_fix, needs_phrase_fix
            )
            data["cover_letter_focus"] = new_focus
            data["cover_letter_paragraphs"] = new_paras
        except Exception:  # noqa: BLE001
            pass

    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_filename_suffix(company: str, role: str) -> str:
    combined = f"{company}_{role}"
    return re.sub(r"[^A-Za-z0-9]+", "_", combined).strip("_")


def _normalise_experience_overrides(raw: dict) -> dict:
    result = {}
    for k, v in raw.items():
        try:
            result[int(k)] = [str(b) for b in v]
        except (ValueError, TypeError):
            continue
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_config(job_description: str) -> tuple[dict, dict, list[str]]:
    """
    Main entry point for the AI engine.

    Returns:
        Tuple of:
          - cv_config (dict): Compatible with generator.py's build_context()
          - cover_letter_content (dict): Keys: recipient, focus, paragraphs
          - ats_keywords (list[str]): Keywords extracted from the JD
    """
    data = _call_llm(job_description)

    company_name = data.get("company_name", "Company")
    target_role = data.get("target_role", "Role")

    cv_config = {
        "company_name": company_name,
        "target_role": target_role,
        "role_badge": data.get("role_badge", target_role.upper()[:30]),
        "pdf_title": f"{company_name} {target_role}",
        "filename_suffix": _build_filename_suffix(company_name, target_role),
        "tagline": data.get("tagline", ""),
        "summary": data.get("summary", ""),
        "skills": data.get("skills", []),
        "experience_overrides": _normalise_experience_overrides(
            data.get("experience_overrides", {})
        ),
    }

    cover_letter_content = {
        "recipient": data.get("cover_letter_recipient", f"Dear {company_name} Hiring Team,"),
        "focus": data.get("cover_letter_focus", ""),
        "paragraphs": data.get("cover_letter_paragraphs", []),
    }

    ats_keywords = data.get("ats_keywords", [])

    return cv_config, cover_letter_content, ats_keywords
