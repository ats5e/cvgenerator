"""
ai_engine.py
AI-powered tailoring engine for DT's CV & Cover Letter Generator.
Calls Claude to analyse a job description and produce a fully tailored
config dict compatible with generator.py and cover_letter_generator.py.
"""
from __future__ import annotations

import json
import os
import re

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# DT's static background — injected into every Claude prompt so the model
# can produce realistic, grounded copy rather than generic filler.
# ---------------------------------------------------------------------------
CANDIDATE_CONTEXT = """
CANDIDATE: Du-Toit Griesel
Location: Dubai, United Arab Emirates
Contact: +971 52 845 5283 | dutoitgriesel@gmail.com | linkedin.com/in/dutoitgriesel
Nationality: South African | Languages: English, Afrikaans

CAREER TIMELINE:
1. Senior Account Manager — Yellow Branding & Digital Consultancy, Dubai (Oct 2025 – Present)
   Core work: leading integrated client accounts; managing scope, timelines, budgets;
   senior stakeholder communication; cross-functional delivery across branding, digital
   and campaign work.

2. Account Manager — Yellow Branding & Digital Consultancy, Dubai (Sep 2023 – Oct 2025)
   Core work: multi-channel brand and digital rollouts; coordinating strategy, creative,
   design and production teams; brief interrogation; scope protection through
   approval and implementation stages.

3. Account Manager — HAASXSWITCH (Haas Advertising x Switch Design), Cape Town (Mar 2022 – Sep 2023)
   Core work: new brand launches; integrated campaigns across traditional, digital and
   retail touchpoints; day-to-day client lead across design, copy and production workstreams.

4. Account Manager — VMLY&R (formerly Geometry Global), Cape Town (May 2020 – Dec 2021)
   Core work: British American Tobacco campaigns during COVID; managing approvals,
   production and delivery remotely; maintaining output quality under tight regulatory
   and operational constraints.

5. Senior Account Executive — Ogilvy & Mather, Cape Town (Jul 2018 – May 2020)
   Core work: retail and integrated projects from briefing through final production;
   handling demanding clients professionally; aligning creative and production teams.

6. Account Executive — Shift ONE Advertising Agency, Cape Town (Nov 2017 – Jul 2018)
   Core work: digital-led agency environment; estimates, trafficking, QA, production
   coordination, day-to-day client communication.

EDUCATION:
- Bachelor's Degree, Integrated Marketing Communication — AAA School of Advertising, Cape Town (2014–2016)
  Specialisations: Account Management, Brand Management, Digital Media Marketing.
- Certificate in Copywriting for a Digital World — AAA School of Advertising

KEY STATS: 8+ years agency experience | UAE and South Africa markets | Yellow, VMLY&R, Ogilvy
"""

SYSTEM_PROMPT = """You are an elite CV writer and ATS optimisation specialist with deep knowledge
of how applicant tracking systems score CVs. Your task is to analyse a job description and produce
a tailored CV configuration and cover letter for Du-Toit Griesel that will:

1. Score highly on ATS keyword matching by using exact phrases from the JD verbatim
2. Sound natural and genuinely written by DT — not a keyword-stuffed robot
3. Directly address the requirements and language of the specific role
4. Position DT's 8+ years of agency experience compellingly for this role

ATS OPTIMISATION RULES (critical — follow these precisely):
- Extract the 12-18 most important keyword PHRASES from the JD (not single words; multi-word phrases score better)
- Use exact JD phrases selectively in the summary and ATS keywords where they genuinely fit
- Mirror the JD's vocabulary throughout — if it says "stakeholder engagement", use that, not "client management"
- Order skills by their frequency and prominence in the JD (most critical first)
- Skills must be concise CV-ready competency labels grounded in Du-Toit's real experience, not copied JD sentences
- Each skill must read like a professional capability heading, not a responsibility, requirement, or qualification
- Experience bullets should directly echo JD requirements — address them head-on
- Summary should sound natural, while embedding JD keywords seamlessly
- Keep experience bullets under 22 words — punchy, active, specific
- The role_badge must be max 4 words in ALL CAPS
- The CV summary is not a cover letter: do not use "I" there
- Read the full job description carefully before writing anything
- The cover letter must be written in first person singular using "I", "me", and "my"
- Never refer to the candidate in the cover letter as "Du-Toit", "DT", "he", "him", or "his"
- The cover letter must be concise, engaging, and clearly structured in four short paragraphs
- The cover letter must pull from Du-Toit's real experience and connect the most relevant roles and strengths to the brief
- Avoid generic filler, repetition, or empty enthusiasm; every sentence should add value

OUTPUT FORMAT: Return ONLY valid JSON, no markdown fences, no explanation. The JSON must match
this exact schema with all field names spelled exactly as shown."""

JSON_SCHEMA = """
{
  "company_name": "string — company name extracted from JD",
  "target_role": "string — exact role title as shown in JD",
  "role_badge": "string — role title in ALL CAPS, max 4 words",
  "tagline": "string — three short keyword phrases separated by | (e.g. 'Brand Strategy | Regional Rollout | Stakeholder Management')",
  "summary": "string — two-sentence CV profile summary. Embed ATS keywords naturally. Do NOT use 'I' — write in implied third person (e.g. 'Brand Manager with...'). End both sentences with a full stop.",
  "skills": ["string array of exactly 10 concise core competencies ordered by JD priority. Each item must be a CV-ready skill heading of 1-4 words, grounded in Du-Toit's actual experience. Do not output requirement sentences, education requirements, language requirements, or copied JD bullets."],
  "experience_overrides": {
    "0": ["string bullet 1 for Yellow SAM role (current, Dubai)", "string bullet 2"],
    "1": ["string bullet 1 for Yellow AM role (Dubai)", "string bullet 2"]
  },
  "ats_keywords": ["array of 12-18 key phrases extracted verbatim from the JD"],
  "cover_letter_recipient": "string — e.g. 'Dear [Company] Hiring Team,'",
  "cover_letter_focus": "string — 3-5 word summary of the letter's angle",
  "cover_letter_paragraphs": [
    "string — opening paragraph (2-3 sentences, concise and engaging) written in first person singular using I/my/me: state role, years experience, and strongest fit for the brief",
    "string — experience paragraph (2-3 sentences, concise and specific) written in first person singular using I/my/me: draw directly from Du-Toit's most relevant real experience and strengths for the JD",
    "string — company/role fit paragraph (2-3 sentences, concise and grounded) written in first person singular using I/my/me: what attracts me to this specific company/role and why that fit makes sense",
    "string — closing paragraph (1-2 sentences, tight and confident) written in first person singular using I/my/me: call to action and thank you"
  ]
}"""

USER_PROMPT_TEMPLATE = """Analyse this job description and produce a tailored CV config for Du-Toit Griesel.

{candidate_context}

JOB DESCRIPTION:
{job_description}

Return a JSON object matching this schema exactly:
{schema}

Remember:
- company_name should be the hiring company (not the recruiter if different)
- target_role should be the exact title from the JD
- Skills must be intelligent CV competencies, not copied job requirements
- Each skill should be short, specific, and believable from Du-Toit's background
- Never include items like degree requirements, language requirements, 'proven experience', or long JD-style responsibility lines in skills
- Read the full job description before drafting the cover letter
- All four cover_letter_paragraphs must be written in first person singular in DT's voice — confident, professional, genuine
- The cover letter must use I/my/me and must never refer to DT by name or as he/him/his
- The cover letter should be concise, engaging, and well structured
- The cover letter should reference specifics from the JD, not generic marketing fluff
- The cover letter should explicitly pull from Du-Toit's real agency experience where relevant
- experience_overrides bullets must directly address what the JD asks for"""

FIRST_PERSON_PATTERN = re.compile(
    r"\b(i|i'm|i'd|i've|i'll|me|my|mine|myself)\b",
    flags=re.IGNORECASE,
)
THIRD_PERSON_PATTERN = re.compile(
    r"\b(du-toit|dt|he|him|his)\b",
    flags=re.IGNORECASE,
)
SKILL_REQUIREMENT_PATTERN = re.compile(
    r"\b("
    r"bachelor|degree|required|preferred|must|plus|proficiency|english|languages|"
    r"track record|proven experience|strong understanding|adept at|ability to|"
    r"experience managing|managing multiple|presenting concepts|award-winning"
    r")\b",
    flags=re.IGNORECASE,
)


def _normalise_quote_chars(value: str) -> str:
    return value.replace("’", "'").replace("‘", "'")


def _cover_letter_needs_first_person_rewrite(paragraphs: list[str]) -> bool:
    combined = _normalise_quote_chars(" ".join(p.strip() for p in paragraphs if str(p).strip()))
    if not combined:
        return False

    first_person_hits = len(FIRST_PERSON_PATTERN.findall(combined))
    third_person_hits = len(THIRD_PERSON_PATTERN.findall(combined))

    return first_person_hits == 0 or third_person_hits > first_person_hits


def _skills_need_polish(skills: list[str]) -> bool:
    cleaned = [str(skill).strip() for skill in skills if str(skill).strip()]
    if len(cleaned) != 10:
        return True

    for skill in cleaned:
        words = re.findall(r"[A-Za-z0-9&/+\-']+", skill)
        if len(words) == 0 or len(words) > 6:
            return True
        if any(mark in skill for mark in [",", ";", ":"]):
            return True
        if SKILL_REQUIREMENT_PATTERN.search(skill):
            return True

    return False


def _polish_skills(
    client: OpenAI,
    company_name: str,
    target_role: str,
    job_description: str,
    skills: list[str],
) -> list[str]:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are refining the core competencies section of a CV for Du-Toit Griesel. "
                    "Read the full job description carefully. "
                    "Return exactly 10 concise, CV-ready skill headings grounded in the candidate's real experience. "
                    "Use JD vocabulary where appropriate, but do not copy JD sentences or requirements. "
                    "Each skill must be 1-4 words where possible and read like a professional competency heading."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    "JOB DESCRIPTION:\n"
                    f"{job_description.strip()}\n\n"
                    "CURRENT SKILLS:\n"
                    f"{json.dumps(skills, ensure_ascii=False)}\n\n"
                    "Rewrite the skills list for the CV. Requirements:\n"
                    "- Return exactly 10 items\n"
                    "- Use concise CV competency headings, not sentences\n"
                    "- Ground every item in Du-Toit's actual experience\n"
                    "- Reflect the role brief intelligently, not mechanically\n"
                    "- Avoid education, language, eligibility, or requirement statements\n"
                    "- Avoid phrases like 'proven experience', 'strong understanding', or copied JD bullets\n"
                    "- Order items by relevance to the role\n"
                    "- Return only JSON with {\"skills\":[...]} for "
                    f"{company_name} / {target_role}"
                ),
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    data = json.loads(raw)

    polished = [str(item).strip() for item in data.get("skills", []) if str(item).strip()]
    if len(polished) == 10:
        return polished
    return skills


def _rewrite_cover_letter_first_person(
    client: OpenAI,
    company_name: str,
    target_role: str,
    paragraphs: list[str],
) -> list[str]:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Rewrite cover letter paragraphs into natural first-person singular voice. "
                    "Use I/my/me. Never refer to the candidate by name or as he/him/his. "
                    "Preserve the original facts, role fit, and confidence."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Rewrite these cover letter paragraphs for "
                    f"{company_name} / {target_role}. "
                    "Keep four paragraphs in the same order and return only JSON with "
                    '{"cover_letter_paragraphs":["...","...","...","..."]}.\n\n'
                    f"Original paragraphs:\n{json.dumps(paragraphs, ensure_ascii=False)}"
                ),
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    data = json.loads(raw)

    rewritten = [str(item).strip() for item in data.get("cover_letter_paragraphs", []) if str(item).strip()]
    if rewritten:
        return rewritten
    return paragraphs


def _polish_cover_letter(
    client: OpenAI,
    company_name: str,
    target_role: str,
    job_description: str,
    focus: str,
    paragraphs: list[str],
) -> tuple[str, list[str]]:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are polishing a professional cover letter for Du-Toit Griesel. "
                    "Read the full job description before writing. "
                    "Return a concise, engaging, highly tailored four-paragraph cover letter in first person singular. "
                    "Use only real experience from the candidate context and the draft. "
                    "Make the structure sharp: opening fit, relevant experience, company/role fit, concise close. "
                    "Avoid generic filler, repetition, and vague praise. "
                    "Never refer to the candidate by name or as he/him/his. "
                    "Keep the tone confident, warm, and commercial."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{CANDIDATE_CONTEXT}\n\n"
                    "JOB DESCRIPTION:\n"
                    f"{job_description.strip()}\n\n"
                    "CURRENT COVER LETTER FOCUS:\n"
                    f"{focus or 'Tailored role fit'}\n\n"
                    "CURRENT COVER LETTER PARAGRAPHS:\n"
                    f"{json.dumps(paragraphs, ensure_ascii=False)}\n\n"
                    "Rewrite this into the strongest possible concise cover letter. Requirements:\n"
                    "- Write in first person singular using I/my/me\n"
                    "- Keep exactly 4 paragraphs\n"
                    "- Make it engaging from the first sentence\n"
                    "- Show that you have read the full job description, not just the title\n"
                    "- Pull from Du-Toit's most relevant real experience and strengths\n"
                    "- Connect those experiences directly to the brief\n"
                    "- Keep it concise and structured, with no fluff\n"
                    "- Do not invent metrics, employers, responsibilities, or achievements\n"
                    "- Return only JSON with keys cover_letter_focus and cover_letter_paragraphs\n"
                    '- cover_letter_paragraphs must be an array of exactly 4 strings'
                ),
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    data = json.loads(raw)

    polished_focus = str(data.get("cover_letter_focus", focus or "")).strip()
    polished_paragraphs = [
        str(item).strip()
        for item in data.get("cover_letter_paragraphs", [])
        if str(item).strip()
    ]

    if len(polished_paragraphs) == 4:
        return polished_focus, polished_paragraphs
    return focus, paragraphs


def _call_llm(job_description: str) -> dict:
    """Call OpenAI API (JSON mode) and return parsed JSON config."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Check your .env file.")

    client = OpenAI(api_key=api_key)

    user_message = USER_PROMPT_TEMPLATE.format(
        candidate_context=CANDIDATE_CONTEXT,
        job_description=job_description.strip(),
        schema=JSON_SCHEMA,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # JSON mode guarantees valid JSON, but strip any stray code fences just in case
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    data = json.loads(raw)

    skills = [str(item).strip() for item in data.get("skills", []) if str(item).strip()]
    if skills and _skills_need_polish(skills):
        try:
            data["skills"] = _polish_skills(
                client,
                data.get("company_name", "Company"),
                data.get("target_role", "Role"),
                job_description,
                skills,
            )
        except Exception:  # noqa: BLE001
            pass

    paragraphs = [str(item).strip() for item in data.get("cover_letter_paragraphs", []) if str(item).strip()]
    focus = str(data.get("cover_letter_focus", "")).strip()

    if paragraphs:
        try:
            polished_focus, polished_paragraphs = _polish_cover_letter(
                client,
                data.get("company_name", "Company"),
                data.get("target_role", "Role"),
                job_description,
                focus,
                paragraphs,
            )
            if polished_focus:
                data["cover_letter_focus"] = polished_focus
            if polished_paragraphs:
                data["cover_letter_paragraphs"] = polished_paragraphs
                paragraphs = polished_paragraphs
        except Exception:  # noqa: BLE001
            pass

    if _cover_letter_needs_first_person_rewrite(paragraphs):
        try:
            data["cover_letter_paragraphs"] = _rewrite_cover_letter_first_person(
                client,
                data.get("company_name", "Company"),
                data.get("target_role", "Role"),
                paragraphs,
            )
        except Exception:  # noqa: BLE001
            pass

    return data


def _build_filename_suffix(company: str, role: str) -> str:
    """Create a safe filename suffix from company and role."""
    combined = f"{company}_{role}"
    return re.sub(r"[^A-Za-z0-9]+", "_", combined).strip("_")


def _normalise_experience_overrides(raw: dict) -> dict:
    """
    Claude returns JSON keys as strings ("0", "1") but generator.py expects int keys.
    Convert and validate.
    """
    result = {}
    for k, v in raw.items():
        try:
            result[int(k)] = [str(b) for b in v]
        except (ValueError, TypeError):
            continue
    return result


def generate_config(job_description: str) -> tuple[dict, dict, list[str]]:
    """
    Main entry point for the AI engine.

    Args:
        job_description: Raw text of the job description.

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
        "role_badge": data.get("role_badge", target_role.upper()),
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
