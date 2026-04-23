"""
ai_engine.py
AI-powered tailoring engine for DT's CV & Cover Letter Generator.
Uses a configurable OpenAI model (default: gpt-5.4) to analyse a job
description and produce tailored CV and cover letter content.

Three-phase architecture:
  Phase 1 — Strategy  : configured model analyses the JD and builds a positioning brief (free text, temp 0.6)
  Phase 2 — CV        : configured model executes all CV fields using the brief          (JSON, temp 0.15)
  Phase 3 — Letter    : configured model executes the cover letter using the brief       (JSON, temp 0.3)

Separating strategy from execution means Phase 1 thinks freely without JSON constraints,
and Phases 2 & 3 each have a clear strategic brief to execute from — rather than doing
analysis and copywriting simultaneously in a single call.
"""
from __future__ import annotations

import json
import os
import re
from typing import Callable

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

_API_TIMEOUT = 90  # seconds for every OpenAI call
_DEFAULT_OPENAI_MODEL = "gpt-5.4"
_OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or _DEFAULT_OPENAI_MODEL).strip() or _DEFAULT_OPENAI_MODEL
ProgressCallback = Callable[[dict], None]


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
# ── PHASE 1: STRATEGY ───────────────────────────────────────────────────────
# The configured model thinks freely as a career strategist — no JSON constraints.
# Output is a plain-text positioning brief used by Phases 2 and 3.
# ---------------------------------------------------------------------------

STRATEGY_SYSTEM_PROMPT = """\
You are a senior career strategist and headhunter with 20 years of experience placing
marketing and brand management professionals across GCC and MENA markets. You think like
a hiring manager's counterpart — ruthlessly focused on what they need to see, not what
a candidate wants to say.

Your output will be used by a professional CV writer in the next step. Be specific,
opinionated, and direct. Name the strongest angles, flag the real gaps, and identify
exactly which vocabulary must appear verbatim. Vague guidance produces weak CVs.

Think out loud. Your analysis quality determines the quality of the CV that follows."""


STRATEGY_USER_TEMPLATE = """\
Analyse this job description against Du-Toit Griesel's background.
Produce a tight positioning brief for the CV writer.

{candidate_context}

━━━ JOB DESCRIPTION ━━━
{job_description}
━━━ END JD ━━━

Work through each section below:

## 1. ROLE DECODE
- Exact title, seniority level, and primary function
- Is this a strategic role, executional role, or hybrid?
- What does success look like in the first 6 months?
- What is the single most important thing a candidate must demonstrate?

## 2. TOP REQUIREMENTS (priority order)
List the 5–7 things the hiring manager most needs to see evidence of.
For each requirement, quote the exact JD phrase that signals it.

## 3. VOCABULARY MAP
List every specific term, tool, market, or metric from the JD that must appear
verbatim in the CV. Be precise.
Format each as: "[exact term]" → appears in: [summary / skills / bullet role 0 / bullet role 1]

## 4. DT'S STRONGEST PROOF POINTS
Which 3–4 specific elements of DT's background most directly prove fit for this role?
Be specific: name the role, the activity, WHY a hiring manager finds it compelling.
Rank by persuasive strength (most compelling first).

## 5. POSITIONING ANGLE
In one sentence: how should DT be framed for this specific role?
This is the strategic spine — every CV field must support it.

## 6. COVER LETTER STRATEGY
- P1 angle: What is the strongest credential to open with? (strategic direction, not the text)
- P2 angle: Which specific experience from DT's background should be the centrepiece paragraph?
- P3 angle: What specific element of the JD (challenge, category, market, scale) should P3 engage with?
- Tone: How should this letter sound? (e.g. peer-to-peer confidence, strategic counsel, executional authority)

## 7. GAPS & GUARDRAILS
What does the JD ask for that DT cannot credibly claim? Be explicit.
What must the CV avoid overstating?"""


# ---------------------------------------------------------------------------
# ── PHASE 2: CV EXECUTION ───────────────────────────────────────────────────
# The configured model executes all CV fields guided by the strategy brief.
# JSON output, low temperature for precision.
# ---------------------------------------------------------------------------

CV_EXECUTION_SYSTEM_PROMPT = """\
You are a world-class CV writer executing a brief prepared by a senior career strategist.
Your output will be printed verbatim in a PDF sent to a real hiring manager at a real company.
It must be better than anything the candidate could write themselves.

You have three inputs:
1. A strategic positioning brief — your spine. Every field must support the positioning angle.
2. The candidate's real background — stay grounded in it. Fabricate nothing.
3. The job description — mirror its exact vocabulary throughout.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATS SCORING MECHANICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Exact phrase matching — "brand P&L" scores more than "budget"
2. Keyword distribution — a phrase in summary + skills + a bullet scores 3× vs once
3. Semantic relevance — ATS checks if your document discusses the same topics as the JD
4. Target: 12–18 key phrases woven naturally across the full document

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CV BULLET RULES — NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TENSE: Role 0 (current) = present tense. Roles 1, 2, 3+ = past tense. No exceptions.

ACTION VERBS: Every bullet starts with a strong, specific verb.
  ✗ "Responsible for", "Worked on", "Helped with", "Involved in", "Supported"
  ✓ Lead, Drive, Manage, Oversee, Direct, Execute, Deliver, Coordinate, Develop, Build

VOCABULARY MIRRORING: Use the JD's exact phrasing inside bullets.
  JD says "A&P budget" → bullet says "A&P budget" (not "marketing spend")
  JD says "shopper marketing" → bullet says "shopper marketing"
  JD says "GCC markets" → bullet mentions GCC

STRUCTURE: [Strong verb] [what] [using what / where] [to what end] — under 22 words

BANNED PATTERNS:
  ✗ "ensuring alignment with strategic objectives"
  ✗ "with a focus on delivering results"
  ✗ "in order to achieve business goals"
  ✗ "managing to meet deadlines"
  ✗ "supporting [noun]" / "discussing [noun]" as the core claim
  ✗ "driving business/overall growth"
  ✗ "for the business / for the team / for the company"
  ✗ "worked on / worked alongside / involved in"

EXAMPLE — for an FMCG Brand Manager JD:
  ✗ WEAK: "Led integrated client accounts, managing scope, timelines, and budgets."
  ✓ STRONG: "Lead 360 FMCG brand campaigns across UAE, managing A&P budgets, agency
             partners, and shopper marketing activations from brief through launch."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILLS RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Exactly 10 items, ordered by prominence in the JD (most critical first)
- 1–4 words each — professional competency headings, not sentences
- Use the JD's preferred terms exactly
- ✗ Never: sentences, requirements, degree/language/eligibility items
- ✓ Good: "Brand Strategy", "A&P Budget Management", "Shopper Marketing"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Two sentences, third-person implied (no "I")
- Sentence 1: [JD role title] with [X years] experience in [top 2 JD themes + sector if named]
- Sentence 2: Strongest credible proof point + positioning statement for this specific role
- Embed 3–4 high-priority ATS keywords naturally
- Do NOT write "[role] candidate" or use weak proof language like "exposure to"
- BANNED: "Proven track record", "Proven ability", "results-driven", "dynamic", "seasoned",
  "passionate", "highly motivated"

Return ONLY valid JSON matching the schema. No markdown fences. No explanation."""


CV_SCHEMA = """{
  "company_name": "string — hiring company name from the JD (not a recruiter name)",
  "target_role": "string — exact role title as it appears in the JD",
  "role_badge": "string — role title in ALL CAPS, max 4 words, e.g. 'SENIOR BRAND MANAGER'",
  "tagline": "string — exactly three keyword phrases separated by ' | ', using JD vocabulary verbatim. E.g. 'Brand Strategy | GCC Market Execution | A&P Budget Management'",
  "summary": "string — two sentences, third-person implied (no I). Opens with JD role title + sector if given. States strongest positioning proof. Under 60 words. No 'Proven track record'.",
  "skills": [
    "exactly 10 items — 1-4 word professional competency headings ordered by JD priority",
    "Use JD exact terminology",
    "No sentences, no requirements, no language/degree items"
  ],
  "experience_overrides": {
    "0": ["Present-tense bullet 1 — current Yellow SAM role (≤22 words, strong verb, JD vocabulary)", "Present-tense bullet 2 (≤22 words)"],
    "1": ["Past-tense bullet 1 — Yellow AM role (≤22 words, strong verb)", "Past-tense bullet 2 (≤22 words)"],
    "2": ["Past-tense bullet 1 — HAASXSWITCH AM role (≤22 words — include only if meaningfully relevant to the JD)", "Past-tense bullet 2 (≤22 words)"]
  },
  "ats_keywords": ["12-18 concise keyword phrases, 2-6 words each, taken verbatim from the JD vocabulary. Use the vocabulary map terms from the strategy brief as your primary source. These are specific terms and phrases — NOT full sentences. E.g. 'A&P budget', 'shopper marketing activations', '360 integrated campaigns', 'GCC markets', 'brand P&L', 'retail activation', 'agency partner management'. Ordered by ATS importance."]
}"""


CV_EXECUTION_USER_TEMPLATE = """\
Execute the CV for Du-Toit Griesel. You have a positioning brief from the senior strategist
and DT's full background below. Every field must serve the positioning angle.

━━━ POSITIONING BRIEF ━━━
{strategy_brief}
━━━ END BRIEF ━━━

{candidate_context}

━━━ JOB DESCRIPTION ━━━
{job_description}
━━━ END JD ━━━

EXECUTION INSTRUCTIONS:
- Use the positioning angle as your spine — every sentence should reinforce it
- Place every vocabulary map term in the location specified
- Build bullets around the proof points identified as DT's strongest
- Do NOT claim anything flagged in Gaps & Guardrails
- The summary and current-role bullets (role 0) are the two most-read fields — write them last and make them exceptional

Return JSON matching this schema:
{cv_schema}

FINAL CHECKLIST:
✓ Role 0 bullets present tense (Lead, Manage, Drive, Oversee)
✓ Roles 1 and 2 bullets past tense (Led, Managed, Drove, Oversaw)
✓ Every bullet opens with a strong action verb — no "Responsible for" or "Worked on"
✓ Every bullet contains at least one JD vocabulary term
✓ No bullet contains: "ensuring alignment", "with a focus on", "in order to", "supporting", "for the business"
✓ Summary names the sector if the JD specifies one
✓ Summary contains NO: "Proven track record", "results-driven", "dynamic", "passionate", "[role] candidate", "exposure to"
✓ ATS keywords are 12–18 concise phrases, each 2–6 words — no single words, no full sentences
✓ Skills ordered by JD priority, using exact JD terminology"""


# ---------------------------------------------------------------------------
# ── PHASE 3: COVER LETTER EXECUTION ────────────────────────────────────────
# Dedicated call focused solely on persuasive writing.
# Has the strategy brief + the CV summary for consistency.
# ---------------------------------------------------------------------------

CL_EXECUTION_SYSTEM_PROMPT = """\
You are a world-class cover letter writer executing a brief prepared by a senior career strategist.
You write as Du-Toit Griesel, in first-person singular (I/me/my).
Never refer to the candidate by name or as he/him/his.

Your letter must read like it was written by a confident peer — not a job seeker.
You have a clear strategic brief with exact angles for each paragraph. Execute them precisely.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVER LETTER RULES — NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VOICE: First-person singular throughout. I / me / my. Zero exceptions.

BANNED OPENERS:
  ✗ "I am thrilled / excited / delighted / pleased to apply"
  ✗ "I am writing to apply for / express my interest in"
  ✗ "I am reaching out regarding"
  ✗ Any sentence starting with "I am [emotion/state]"

BANNED PHRASES (anywhere in the letter):
  ✗ "resonates with my [anything]" — always hollow
  ✗ "passion for" / "passionate about"
  ✗ "I am eager to bring"
  ✗ "I believe I would be a great asset"
  ✗ "perfect fit" / "dream role"
  ✗ "proven track record"
  ✗ "ensuring alignment" — same filler as weak CV bullets
  ✗ "directly reflecting the [core] requirements [of your position]" — template language
  ✗ "positions me to [effectively] contribute to your [team's] success" — generic
  ✗ Any wording that frames the move as a "transition" or stretch rather than existing fit
  ✗ "I look forward to hearing from you soon"
  ✗ "Thank you for your time and consideration" as a standalone sentence

PARAGRAPH STRUCTURE:
  P1 (2–3 sentences):
    Open as a peer, not an applicant. Lead with seniority + specific credential + clearest fit.
    Model structure: "With [X] years of [relevant experience], I bring [what this role needs]
    directly to [company name]'s [challenge/team/market]."

  P2 (2–3 sentences):
    Your most relevant real experience mapped to 2–3 specific JD requirements.
    Name real employers, real markets, real deliverables — no vague claims.

  P3 (2–3 sentences):
    Something specific about THIS company or role that genuinely connects.
    Not "your values" or "your culture" — engage with the category, scale, challenge, or market
    as described in the JD.

  P4 (1–2 sentences):
    Direct, confident close. Invite a conversation. No enthusiasm language.
    Example: "I would welcome the opportunity to discuss how my background in [X] can
    support [company]'s [specific goal]. Thank you for considering my application."

Return ONLY valid JSON matching the schema. No markdown fences. No explanation."""


CL_SCHEMA = """{
  "cover_letter_recipient": "string — e.g. 'Dear [Company] Hiring Team,'",
  "cover_letter_focus": "string — 3-5 word internal label, e.g. 'FMCG Brand Leadership, GCC'",
  "cover_letter_paragraphs": [
    "Para 1 (2-3 sentences): Peer-level opening. Lead with seniority + specific credential. NO banned opener.",
    "Para 2 (2-3 sentences): Specific real experience mapped to 2-3 JD requirements. Name real places, deliverables, contexts.",
    "Para 3 (2-3 sentences): Something specific from the JD — category, scale, challenge, or market. Not values.",
    "Para 4 (1-2 sentences): Direct confident close. Invite a conversation. No banned phrases."
  ]
}"""


CL_EXECUTION_USER_TEMPLATE = """\
Write a cover letter for Du-Toit Griesel using the positioning brief below.

━━━ POSITIONING BRIEF ━━━
{strategy_brief}
━━━ END BRIEF ━━━

{candidate_context}

━━━ JOB DESCRIPTION ━━━
{job_description}
━━━ END JD ━━━

CV CONTEXT (maintain consistency with this):
  Summary: {cv_summary}
  Target role: {target_role}
  Target company: {company_name}

EXECUTION INSTRUCTIONS:
- Follow the cover letter strategy from the brief exactly
- Build P1 around the P1 angle identified
- Build P2 around the P2 experience identified — name it specifically
- Build P3 around the specific JD element identified for P3 — not values, not culture
- P4 closes with confidence and a clear invitation to talk
- Every sentence must earn its place — cut anything generic

Return JSON matching this schema:
{cl_schema}

FINAL CHECKLIST:
✓ P1 does NOT open with "I am thrilled/excited/delighted/writing to apply"
✓ P2 names a real employer, real market, or real deliverable — and contains NO filler
✓ P3 engages with a specific element of the JD — the category, challenge, or market; NOT "your culture" or "your values"
✓ No paragraph contains: "resonates with my", "passion for", "proven track record", "ensuring alignment", "directly reflecting the requirements", or transition framing
✓ Every paragraph in first-person singular (I/me/my) — zero third-person references
✓ P4 is a direct two-sentence close"""


# ---------------------------------------------------------------------------
# Quality-gate patterns — safety nets that fire if a phase produces weak output
# ---------------------------------------------------------------------------

_FIRST_PERSON_RE = re.compile(
    r"\b(i|i'm|i'd|i've|i'll|me|my|mine|myself)\b", flags=re.IGNORECASE
)
_THIRD_PERSON_RE = re.compile(
    r"\b(du-toit|dt|he|him|his)\b", flags=re.IGNORECASE
)

_BANNED_CL_RE = re.compile(
    r"i am (thrilled|excited|delighted|pleased|happy|writing to apply|reaching out)|"
    r"resonates? with my|"
    r"passion for|passionate about|"
    r"i am eager to bring|"
    r"perfect fit|dream role|"
    r"i believe i (would be|will be) a great asset|"
    r"proven track record|"
    r"ensuring alignment|"
    r"directly reflecting the (core )?requirements|"
    r"positions me to (effectively )?contribute to your|"
    r"transition i am set up to make|"
    r"\bcareer transition\b|"
    r"\bthis transition\b|"
    r"thank you for your time and consideration$",
    flags=re.IGNORECASE,
)

_BAD_SKILL_RE = re.compile(
    r"\b("
    r"bachelor|degree|required|preferred|must|plus|proficiency|english|languages|"
    r"track record|proven experience|strong understanding|adept at|ability to|"
    r"experience managing|managing multiple|presenting concepts|award-winning|"
    r"years of experience|demonstrated"
    r")\b",
    flags=re.IGNORECASE,
)

_WEAK_BULLET_RE = re.compile(
    r"ensuring alignment|"
    r"with a focus on|"
    r"in order to|"
    r"managing to|"
    r"\bsupport(ing|ed)\b|"
    r"\bdiscuss(ing|ed)\b|"
    r"\bexposure to\b|"
    r"\bfor the (business|team|company|organisation|organization)\b|"
    r"\bdriving (business |overall )?growth\b|"
    r"\bresponsible for\b|"
    r"\bworked (on|with|alongside)\b|"
    r"\binvolved in\b",
    flags=re.IGNORECASE,
)


def _normalise_quotes(text: str) -> str:
    return (
        text.replace("\u2018", "'").replace("\u2019", "'")
            .replace("\u201c", '"').replace("\u201d", '"')
    )


# ---------------------------------------------------------------------------
# Quality-gate functions — return True if a fix pass is needed
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


def _keywords_need_polish(keywords: list[str]) -> bool:
    cleaned = [str(k).strip() for k in keywords if str(k).strip()]
    if not 12 <= len(cleaned) <= 18:
        return True
    for keyword in cleaned:
        words = re.findall(r"[A-Za-z0-9&/+\-']+", keyword)
        if len(words) < 2 or len(words) > 6:
            return True
        if any(ch in keyword for ch in ("\n", ".", ";", ":")):
            return True
    return False


def _bullets_need_improvement(experience_overrides: dict) -> bool:
    all_bullets = []
    for bullets in experience_overrides.values():
        all_bullets.extend(str(b) for b in bullets if str(b).strip())
    if not all_bullets:
        return False
    return bool(_WEAK_BULLET_RE.search(" ".join(all_bullets)))


# ---------------------------------------------------------------------------
# Targeted fix passes — each fires only when its quality gate fails
# ---------------------------------------------------------------------------

def _fix_skills(client: OpenAI, company: str, role: str, jd: str, skills: list[str]) -> list[str]:
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
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
                    f'Return only JSON: {{"skills":[...10 items...]}}'
                ),
            },
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    result = [str(s).strip() for s in json.loads(raw).get("skills", []) if str(s).strip()]
    return result if len(result) == 10 else skills


def _fix_bullets(client: OpenAI, company: str, role: str, jd: str, overrides: dict) -> dict:
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
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
                    "No filler: no 'ensuring alignment', 'with a focus on', 'in order to', "
                    "'supporting', 'discussing', 'responsible for', 'worked on'. Under 22 words each. "
                    "Stay grounded — do not invent metrics or achievements."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    f"JOB DESCRIPTION:\n{jd.strip()}\n\n"
                    f"CURRENT BULLETS (need fixing):\n{json.dumps(overrides, ensure_ascii=False)}\n\n"
                    "Rewrite to be punchy, JD-specific, and tense-correct. "
                    'Return JSON: {"experience_overrides": {"0": [...], "1": [...], "2": [...]}}'
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


def _fix_keywords(client: OpenAI, company: str, role: str, jd: str, keywords: list[str]) -> list[str]:
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.1,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Rewrite this ATS keyword list for Du-Toit Griesel. "
                    "Return 12-18 concise keyword phrases extracted from the job description. "
                    "Each keyword must be 2-6 words, use the JD's exact vocabulary, and be ordered by ATS importance. "
                    "No full sentences. No single-word items unless they are part of a multi-word phrase."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    f"JOB DESCRIPTION:\n{jd.strip()}\n\n"
                    f"CURRENT ATS KEYWORDS (need fixing):\n{json.dumps(keywords, ensure_ascii=False)}\n\n"
                    'Return only JSON: {"ats_keywords":[...12-18 concise phrases...]}'
                ),
            },
        ],
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.choices[0].message.content.strip(), flags=re.MULTILINE)
    result = [str(k).strip() for k in json.loads(raw).get("ats_keywords", []) if str(k).strip()]
    return result if not _keywords_need_polish(result) else keywords


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
        issues.append(
            "rewrite into first-person singular (I/me/my) — "
            "never refer to the candidate by name or as he/him/his"
        )
    if fix_phrases:
        issues.append(
            "remove ALL banned phrases — replace each with confident, specific language: "
            "'thrilled/excited/delighted to apply', "
            "'resonates with my [anything]', "
            "'passion for', "
            "'eager to bring my skills', "
            "'I believe I would be a great asset', "
            "'proven track record', "
            "'ensuring alignment', "
            "'directly reflecting the [core] requirements', "
            "'positions me to [effectively] contribute to your [team's] success'. "
            "These are template phrases that make CVs look generic — replace every instance."
        )

    issue_text = " AND ".join(issues) if issues else "polish into the strongest possible version"

    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
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
                    "P3: Something specific from the JD — category, challenge, or scale. "
                    "P4: Direct close, two sentences max. "
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
                    'Return JSON: {"cover_letter_focus": "...", "cover_letter_paragraphs": ["p1","p2","p3","p4"]}'
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


def _emit_progress(
    progress_callback: ProgressCallback | None,
    message: str,
    phase: str,
    progress: int,
) -> None:
    if progress_callback is None:
        return
    progress_callback({
        "status": "ai_phase",
        "message": message,
        "phase": phase,
        "progress": progress,
    })


# ---------------------------------------------------------------------------
# ── Phase execution functions ───────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _call_strategy(client: OpenAI, job_description: str) -> str:
    """
    Phase 1: free-text positioning brief.
    High temperature so the model thinks creatively about angles.
    Returns the brief as a plain string.
    """
    user_message = STRATEGY_USER_TEMPLATE.format(
        candidate_context=CANDIDATE_CONTEXT,
        job_description=job_description.strip(),
    )
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.6,
        timeout=_API_TIMEOUT,
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return resp.choices[0].message.content.strip()


def _call_cv(client: OpenAI, strategy_brief: str, job_description: str) -> dict:
    """
    Phase 2: execute all CV fields using the strategy brief.
    Low temperature for precise, consistent output.
    Returns the parsed JSON dict.
    """
    user_message = CV_EXECUTION_USER_TEMPLATE.format(
        strategy_brief=strategy_brief,
        candidate_context=CANDIDATE_CONTEXT,
        job_description=job_description.strip(),
        cv_schema=CV_SCHEMA,
    )
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.15,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CV_EXECUTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        resp.choices[0].message.content.strip(),
        flags=re.MULTILINE,
    )
    return json.loads(raw)


def _call_cover_letter(
    client: OpenAI,
    strategy_brief: str,
    job_description: str,
    cv_data: dict,
) -> dict:
    """
    Phase 3: execute the cover letter using the strategy brief + CV context.
    Slightly higher temperature for natural persuasive voice.
    Returns the parsed JSON dict.
    """
    user_message = CL_EXECUTION_USER_TEMPLATE.format(
        strategy_brief=strategy_brief,
        candidate_context=CANDIDATE_CONTEXT,
        job_description=job_description.strip(),
        cv_summary=cv_data.get("summary", ""),
        target_role=cv_data.get("target_role", ""),
        company_name=cv_data.get("company_name", ""),
        cl_schema=CL_SCHEMA,
    )
    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.3,
        timeout=_API_TIMEOUT,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CL_EXECUTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        resp.choices[0].message.content.strip(),
        flags=re.MULTILINE,
    )
    return json.loads(raw)


# ---------------------------------------------------------------------------
# ── Main orchestrator ───────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _call_llm(job_description: str, progress_callback: ProgressCallback | None = None) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Check your .env file.")

    client = OpenAI(api_key=api_key)

    # ── Phase 1: Strategy brief ───────────────────────────────────────────
    _emit_progress(progress_callback, "Building strategic positioning brief…", "strategy", 24)
    strategy_brief = _call_strategy(client, job_description)

    # ── Phase 2: CV execution ─────────────────────────────────────────────
    _emit_progress(progress_callback, "Drafting tailored CV content…", "cv_draft", 34)
    cv_data = _call_cv(client, strategy_brief, job_description)

    company = cv_data.get("company_name", "Company")
    role = cv_data.get("target_role", "Role")

    # Skills quality gate
    skills = [str(s).strip() for s in cv_data.get("skills", []) if str(s).strip()]
    if skills and _skills_need_polish(skills):
        try:
            _emit_progress(progress_callback, "Refining skills language…", "skills_fix", 40)
            cv_data["skills"] = _fix_skills(client, company, role, job_description, skills)
        except Exception:  # noqa: BLE001
            pass

    # ATS keywords quality gate
    keywords = [str(k).strip() for k in cv_data.get("ats_keywords", []) if str(k).strip()]
    if keywords and _keywords_need_polish(keywords):
        try:
            _emit_progress(progress_callback, "Cleaning ATS keyword phrases…", "keyword_fix", 44)
            cv_data["ats_keywords"] = _fix_keywords(client, company, role, job_description, keywords)
        except Exception:  # noqa: BLE001
            pass

    # Bullets quality gate
    raw_overrides = cv_data.get("experience_overrides", {})
    if raw_overrides and _bullets_need_improvement(raw_overrides):
        try:
            _emit_progress(progress_callback, "Tightening experience bullets…", "bullet_fix", 48)
            fixed = _fix_bullets(client, company, role, job_description, raw_overrides)
            if fixed:
                cv_data["experience_overrides"] = fixed
        except Exception:  # noqa: BLE001
            pass

    # ── Phase 3: Cover letter execution ──────────────────────────────────
    _emit_progress(progress_callback, "Drafting cover letter…", "cover_letter", 54)
    cl_data = _call_cover_letter(client, strategy_brief, job_description, cv_data)

    # Cover letter quality gates
    paragraphs = [str(p).strip() for p in cl_data.get("cover_letter_paragraphs", []) if str(p).strip()]
    focus = str(cl_data.get("cover_letter_focus", "")).strip()
    needs_voice_fix = _cover_letter_needs_first_person_fix(paragraphs)
    needs_phrase_fix = _cover_letter_has_banned_phrases(paragraphs)

    if paragraphs and (needs_voice_fix or needs_phrase_fix):
        try:
            _emit_progress(progress_callback, "Polishing cover letter language…", "cover_letter_fix", 60)
            new_focus, new_paras = _fix_cover_letter(
                client, company, role, job_description, focus,
                paragraphs, needs_voice_fix, needs_phrase_fix,
            )
            cl_data["cover_letter_focus"] = new_focus
            cl_data["cover_letter_paragraphs"] = new_paras
        except Exception:  # noqa: BLE001
            pass

    return {**cv_data, **cl_data}


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

def generate_config(
    job_description: str,
    progress_callback: ProgressCallback | None = None,
) -> tuple[dict, dict, list[str]]:
    """
    Main entry point for the AI engine.

    Returns:
        Tuple of:
          - cv_config (dict):              Compatible with generator.py's build_context()
          - cover_letter_content (dict):   Keys: recipient, focus, paragraphs
          - ats_keywords (list[str]):       Keywords extracted from the JD
    """
    data = _call_llm(job_description, progress_callback=progress_callback)

    company_name = str(data.get("company_name") or "").strip() or "Company"
    target_role = str(data.get("target_role") or "").strip() or "Role"

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


# ---------------------------------------------------------------------------
# Application question answering — single focused call, no strategy phase
# ---------------------------------------------------------------------------

QUESTION_SYSTEM_PROMPT = """\
You write application question answers on behalf of Du-Toit Griesel, a senior marketing
and brand management professional currently based in Dubai.

RULES:
- First-person throughout (I / me / my) — never refer to him by name or as he/him/his
- 150–200 words — substantive enough to persuade, short enough to paste into a form field
- Specific — ground every claim in a real role, real employer, real market, or real deliverable
  from his background. No generic claims about "my experience" without naming the context.
- Start with your strongest, most relevant point — no warm-up, no scene-setting sentence
- Sound like a confident professional answering a direct question — not a cover letter

BANNED OPENERS:
✗ "I have always been passionate about…"
✗ "This role excites me because…"
✗ "I am thrilled / excited / delighted…"
✗ "Throughout my career…"
✗ "Having spent [X] years…"

BANNED PHRASES (anywhere in the answer):
✗ "passion for" / "passionate about"
✗ "I am eager to bring"
✗ "proven track record"
✗ "results-driven"
✗ "I would be a great fit" / "perfect fit"
✗ "resonates with me"
✗ "I look forward to contributing"
✗ "goes without saying"

Return ONLY the answer text. No label, no "Answer:" prefix, no preamble. Just the answer, ready to paste."""


def answer_question(
    job_description: str,
    question: str,
    company_name: str = "",
    role_title: str = "",
) -> str:
    """
    Generate a tailored answer to a single application screening question for Du-Toit.
    Returns plain text ready to copy-paste into an application form.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Check your .env file.")

    client = OpenAI(api_key=api_key)

    context_line = ""
    if role_title and company_name:
        context_line = f"Applying for: {role_title} at {company_name}\n\n"
    elif role_title:
        context_line = f"Applying for: {role_title}\n\n"
    elif company_name:
        context_line = f"Applying to: {company_name}\n\n"

    user_message = (
        f"{context_line}"
        f"JOB DESCRIPTION:\n{job_description.strip()}\n\n"
        f"{CANDIDATE_CONTEXT}\n\n"
        f"APPLICATION QUESTION:\n{question.strip()}\n\n"
        "Write a tailored answer (150–200 words). "
        "Ground every sentence in real, specific experience. "
        "Start with the single strongest, most relevant point."
    )

    resp = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.4,
        timeout=_API_TIMEOUT,
        messages=[
            {"role": "system", "content": QUESTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return resp.choices[0].message.content.strip()
