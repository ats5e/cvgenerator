from __future__ import annotations

import copy
import html
import re
import subprocess
import tempfile
from pathlib import Path
from string import Template

from pdf_fallback import build_cv_pdf_bytes

CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PROJECT_DIR = Path(__file__).resolve().parent
RUNTIME_OUTPUT_DIR = Path(tempfile.gettempdir()) / "dt_cv_generator"

PROFILE = {
    "first_name": "Du-Toit",
    "last_name": "Griesel",
    "location": "Dubai, United Arab Emirates",
    "phone": "+971 52 845 5283",
    "email": "dutoitgriesel@gmail.com",
    "linkedin": "linkedin.com/in/dutoitgriesel",
    "footer_subtitle": "South African | English, Afrikaans | References available on request",
}

DEFAULT_RENDER_OPTIONS = {
    "design_style": "signature",
    "include_photo": True,
    "contact_mode": "full",
    "show_highlight_strip": True,
}

COMMON_STATS = [
    {"number": "8+", "label": "years agency experience"},
    {"number": "2", "label": "markets: UAE and South Africa"},
    {"number": "3", "label": "Yellow, VMLY&R, Ogilvy"},
]

BASE_EXPERIENCE = [
    {
        "title": "Senior Account Manager",
        "date": "Oct 2025 - Present",
        "company": "Yellow Branding & Digital Consultancy",
        "location": "Dubai, UAE",
        "bullets": [
            "Lead integrated client accounts in Dubai, managing scope, timelines, budgets and cross-functional delivery across branding, digital and campaign work.",
            "Own senior stakeholder communication, status reporting and handover from briefing through production, launch and post-campaign follow-up.",
        ],
    },
    {
        "title": "Account Manager",
        "date": "Sep 2023 - Oct 2025",
        "company": "Yellow Branding & Digital Consultancy",
        "location": "Dubai, UAE",
        "bullets": [
            "Managed multi-channel brand and digital rollouts for UAE clients, coordinating strategy, creative, design and production teams to meet fast timelines.",
            "Wrote and interrogated briefs, aligned internal teams on deliverables, and protected project scope through approval and implementation stages.",
        ],
    },
    {
        "title": "Account Manager",
        "date": "Mar 2022 - Sep 2023",
        "company": "HAASXSWITCH (Haas Advertising x Switch Design)",
        "location": "Cape Town, South Africa",
        "bullets": [
            "Project-managed new brand launches and integrated campaigns across traditional, digital and retail touchpoints after the agency merger.",
            "Acted as the day-to-day client lead across design, copy and production workstreams, keeping multiple deliverables moving at once.",
        ],
    },
    {
        "title": "Account Manager",
        "date": "May 2020 - Dec 2021",
        "company": "VMLY&R (formerly Geometry Global)",
        "location": "Cape Town, South Africa",
        "bullets": [
            "Managed British American Tobacco campaigns through remote working conditions during COVID, coordinating approvals, production and delivery with minimal supervision.",
            "Maintained output quality and client service standards under tight regulatory and operational constraints.",
        ],
    },
    {
        "title": "Senior Account Executive",
        "date": "Jul 2018 - May 2020",
        "company": "Ogilvy & Mather",
        "location": "Cape Town, South Africa",
        "bullets": [
            "Ran retail and integrated projects from briefing to final production and was commended by senior leadership for taking ownership without close supervision.",
            "Built a reputation for handling demanding clients professionally while keeping creative and production teams aligned.",
        ],
    },
    {
        "title": "Account Executive",
        "date": "Nov 2017 - Jul 2018",
        "company": "Shift ONE Advertising Agency",
        "location": "Cape Town, South Africa",
        "bullets": [
            "Started in a digital-led agency environment covering estimates, trafficking, QA, production coordination and day-to-day client communication.",
        ],
    },
]

BASE_EDUCATION = [
    {
        "degree": "Bachelor's Degree, Integrated Marketing Communication",
        "school": "AAA School of Advertising - Cape Town, South Africa",
        "year": "2014 - 2016",
        "details": "Specialisations: Account Management, Brand Management, Digital Media Marketing.",
    },
    {
        "degree": "Certificate in Copywriting for a Digital World",
        "school": "AAA School of Advertising - Cape Town, South Africa",
        "year": "",
        "details": "",
    },
]

ROLE_CONFIGS = [
    {
        "company_name": "Duolingo",
        "target_role": "Regional Marketing Manager, MENA",
        "role_badge": "REGIONAL MARKETING MANAGER",
        "pdf_title": "Duolingo Regional Marketing Manager",
        "filename_suffix": "Duolingo_RegionalMarketingManager",
        "tagline": "Regional Marketing | Localisation | Integrated Campaigns",
        "summary": "Regional Marketing Manager with 8+ years of experience delivering integrated campaigns, brand rollouts and local market execution across the UAE and South Africa. Experienced in translating strategic briefs into locally relevant digital, content and retail activity, coordinating cross-functional teams, and keeping stakeholders aligned across timelines, budgets and launch plans. Strong fit for MENA roles spanning localisation, campaign delivery, brand partnerships and regional growth marketing.",
        "skills": [
            "Regional marketing strategy",
            "Localisation planning",
            "Integrated campaign management",
            "Brand partnerships",
            "Social and content strategy",
            "Market insight analysis",
            "Cross-functional coordination",
            "Agency and stakeholder management",
            "Budget and timeline control",
            "Campaign reporting",
        ],
        "experience_overrides": {
            0: [
                "Lead UAE-based integrated campaigns for clients with regional audiences, translating strategic briefs into local market plans across digital, content and rollout activity.",
                "Coordinate strategy, creative, design and production teams to deliver launches on time while keeping regional stakeholders aligned on messaging, budget and approvals.",
            ],
            1: [
                "Managed brand and digital rollouts across Dubai, adapting campaign assets for local execution across web, social, retail and environmental touchpoints.",
                "Built clear status and approval processes to keep fast-turnaround regional work moving across multiple teams and suppliers.",
            ],
        },
    },
    {
        "company_name": "Careem",
        "target_role": "Key Account Manager",
        "role_badge": "KEY ACCOUNT MANAGER",
        "pdf_title": "Careem Key Account Manager",
        "filename_suffix": "Careem_KeyAccountManager",
        "tagline": "Client Growth | Stakeholders | Delivery",
        "summary": "Key Account Manager with 8+ years of experience leading client portfolios, campaign delivery and cross-functional coordination in fast-paced agency environments. Strong background in stakeholder management, retention, reporting, issue resolution and commercial account growth across Dubai and Cape Town. Well suited to high-touch client roles where partner performance, service quality and long-term relationship management are core to success.",
        "skills": [
            "Key account management",
            "Client retention",
            "Account growth planning",
            "Stakeholder management",
            "Performance reporting",
            "Issue resolution",
            "SLA and delivery management",
            "Cross-functional coordination",
            "Commercial negotiations",
            "Campaign optimisation",
        ],
        "experience_overrides": {
            0: [
                "Manage senior client relationships across multiple accounts, leading planning, delivery reviews, issue resolution and next-step recommendations.",
                "Keep scopes, budgets, timelines and internal teams aligned to protect service quality and support long-term client retention.",
            ],
            1: [
                "Managed day-to-day relationships on fast-moving Dubai accounts, coordinating deliverables across strategy, creative, design and production teams.",
                "Turned client requests into clear workstreams, status reports and approvals to keep campaigns moving and resolve blockers quickly.",
            ],
        },
    },
    {
        "company_name": "General",
        "target_role": "Client Development Manager",
        "role_badge": "CLIENT DEVELOPMENT MANAGER",
        "pdf_title": "Client Development Manager",
        "filename_suffix": "Client_Development_Manager",
        "tagline": "Clienteling | Omnichannel Experience | Retention",
        "summary": "Client development and account management professional with 8+ years of experience delivering premium brand campaigns, retail activations and personalised communications across agency environments in Dubai and Cape Town. Brings strong stakeholder management, brand stewardship, event coordination and omnichannel execution across boutique, experiential and digital touchpoints. Well suited to client development roles focused on customer retention, CRM and elevated service standards.",
        "skills": [
            "Client development",
            "Customer retention",
            "Clienteling and CRM",
            "Premium retail experience",
            "Omnichannel campaign execution",
            "Event and activation planning",
            "Stakeholder management",
            "Brand standards and governance",
            "Performance reporting",
            "Cross-functional coordination",
        ],
        "experience_overrides": {
            0: [
                "Lead brand and experience delivery across premium-facing accounts, coordinating multiple teams to execute polished work across retail, digital and campaign touchpoints.",
                "Maintain close stakeholder communication and detailed execution standards from briefing through rollout, launch and post-campaign follow-up.",
            ],
            1: [
                "Managed brand and rollout projects where consistency, presentation quality and client service were critical across digital and physical touchpoints.",
                "Coordinated designers, copywriters and production partners to deliver high-touch brand assets on time and to standard.",
            ],
        },
    },
    {
        "company_name": "Dior",
        "target_role": "Client Development Manager",
        "role_badge": "CLIENT DEVELOPMENT MANAGER",
        "pdf_title": "Dior Client Development Manager",
        "filename_suffix": "Dior_Client_Development_Manager",
        "tagline": "Clienteling | Omnichannel Experience | Retention",
        "summary": "Client development and account management professional with 8+ years of experience delivering premium brand campaigns, retail activations and personalised communications across agency environments in Dubai and Cape Town. Brings strong stakeholder management, brand stewardship, event coordination and omnichannel execution across boutique, experiential and digital touchpoints. Well suited to luxury client development roles focused on customer retention, clienteling, CRM and elevated service standards.",
        "skills": [
            "Client development",
            "Customer retention",
            "Clienteling and CRM",
            "Premium retail experience",
            "Omnichannel campaign execution",
            "Event and activation planning",
            "Stakeholder management",
            "Brand standards and governance",
            "Performance reporting",
            "Cross-functional coordination",
        ],
        "experience_overrides": {
            0: [
                "Lead brand and experience delivery across premium-facing accounts, coordinating multiple teams to execute polished work across retail, digital and campaign touchpoints.",
                "Maintain close stakeholder communication and detailed execution standards from briefing through rollout, launch and post-campaign follow-up.",
            ],
            1: [
                "Managed brand and rollout projects where consistency, presentation quality and client service were critical across digital and physical touchpoints.",
                "Coordinated designers, copywriters and production partners to deliver high-touch brand assets on time and to standard.",
            ],
        },
    },
    {
        "company_name": "Spotify",
        "target_role": "Product Marketing Manager, Programmatic",
        "role_badge": "PRODUCT MARKETING MANAGER",
        "pdf_title": "Spotify Product Marketing Manager",
        "filename_suffix": "Spotify_ProductMarketingManager",
        "tagline": "Go-to-Market | Messaging | Digital Media",
        "summary": "Product Marketing Manager profile with 8+ years of experience translating digital capabilities into clear client-facing propositions, launch plans and integrated campaign execution. Combines agency-side experience in digital, content, retail and brand rollout with strong cross-functional coordination across strategy, creative, media and production. Well suited to product marketing roles spanning go-to-market planning, positioning, sales enablement and campaign performance storytelling.",
        "skills": [
            "Product marketing",
            "Go-to-market planning",
            "Positioning and messaging",
            "Programmatic advertising",
            "Sales enablement",
            "Launch management",
            "Customer insight analysis",
            "Cross-functional leadership",
            "Campaign performance reporting",
            "Integrated marketing",
        ],
        "experience_overrides": {
            0: [
                "Translate complex digital and brand initiatives into clear internal briefs, launch plans and client-facing narratives across multiple accounts.",
                "Coordinate cross-functional teams across strategy, creative, production and digital delivery to bring campaigns to market on time.",
            ],
            1: [
                "Managed multi-channel rollouts across web, content and brand touchpoints, aligning internal teams on deliverables, timelines and handover requirements.",
                "Supported campaign reporting and client communication by turning project progress into clear status updates and action plans.",
            ],
        },
    },
    {
        "company_name": "P&G",
        "target_role": "Brand Manager",
        "role_badge": "BRAND MANAGER",
        "pdf_title": "P&G Brand Manager",
        "filename_suffix": "PandG_BrandManager",
        "tagline": "Brand Strategy | Rollout | Market Execution",
        "summary": "Brand Manager with 8+ years of experience supporting brand strategy, integrated campaign planning and market rollout across agency environments in the UAE and South Africa. Strong background in brief development, stakeholder alignment, brand stewardship and launch execution across digital, retail and shopper touchpoints. Well suited to FMCG brand roles where consumer insight, agency management and disciplined delivery are essential.",
        "skills": [
            "Brand management",
            "Integrated campaign planning",
            "Consumer insight translation",
            "Brand positioning",
            "Agency management",
            "Budget tracking",
            "Retail and shopper activation",
            "Launch execution",
            "Cross-functional leadership",
            "Brand governance",
        ],
        "experience_overrides": {
            0: [
                "Lead integrated brand work for UAE clients, taking briefs from strategic input through rollout, launch coordination and stakeholder approvals.",
                "Balance timelines, budgets and cross-functional teams to keep brand execution consistent across digital, retail and campaign touchpoints.",
            ],
            1: [
                "Managed brand development and rollout projects in Dubai, ensuring positioning, messaging and visual execution stayed aligned through delivery.",
                "Partnered with strategy, creative and production teams to move campaigns from brief to market-ready execution.",
            ],
            2: [
                "Project-managed new brand launches across identity, campaign and retail touchpoints, supporting go-to-market readiness and day-to-day client coordination.",
                "Worked across design, copy and production teams to keep brand work commercially grounded and execution-ready.",
            ],
        },
    },
    {
        "company_name": "Lipton",
        "target_role": "Brand Manager",
        "role_badge": "BRAND MANAGER",
        "pdf_title": "Lipton Brand Manager",
        "filename_suffix": "Lipton_BrandManager",
        "tagline": "FMCG Marketing | Launches | Rollout",
        "summary": "Brand Manager with 8+ years of experience delivering integrated brand programmes, launch support and multi-channel campaign execution for consumer-facing businesses. Brings strong grounding in brand positioning, cross-functional coordination, retail activation and rollout governance, with hands-on experience across Dubai and South Africa. Well suited to FMCG brand roles that require agency management, packaging or launch coordination, and disciplined execution across markets.",
        "skills": [
            "Brand management",
            "FMCG marketing",
            "Integrated communications",
            "Packaging and rollout coordination",
            "Retail activation",
            "Agency management",
            "Budget and timeline control",
            "Launch planning",
            "Consumer insight analysis",
            "Cross-functional delivery",
        ],
        "experience_overrides": {
            0: [
                "Lead integrated brand work for UAE clients, taking briefs from strategic input through rollout, launch coordination and stakeholder approvals.",
                "Balance timelines, budgets and cross-functional teams to keep brand execution consistent across digital, retail and campaign touchpoints.",
            ],
            1: [
                "Managed brand development and rollout projects in Dubai, ensuring positioning, messaging and visual execution stayed aligned through delivery.",
                "Partnered with strategy, creative and production teams to move campaigns from brief to market-ready execution.",
            ],
            2: [
                "Project-managed new brand launches across identity, campaign and retail touchpoints, supporting go-to-market readiness and day-to-day client coordination.",
                "Worked across design, copy and production teams to keep brand work commercially grounded and execution-ready.",
            ],
        },
    },
    {
        "company_name": "Alabbar",
        "target_role": "Brand Marketing Manager",
        "role_badge": "BRAND MARKETING MANAGER",
        "pdf_title": "Alabbar Brand Marketing Manager",
        "filename_suffix": "Alabbar_BrandMarketingManager",
        "tagline": "Content | Campaigns | Guest Experience",
        "summary": "Brand Marketing Manager with 8+ years of experience building campaigns, content and launch plans for customer-facing brands across retail, hospitality-adjacent and integrated agency environments. Strong background in concept development, stakeholder management, social and content production, and rollout execution across physical and digital touchpoints. Well suited to F&B and lifestyle roles focused on guest experience, seasonal campaigns and on-brand market execution.",
        "skills": [
            "Brand marketing",
            "Campaign planning",
            "Social and content production",
            "Retail and in-store marketing",
            "Experiential activations",
            "Copywriting and briefing",
            "Stakeholder management",
            "Timeline and budget control",
            "Launch execution",
            "Cross-functional coordination",
        ],
        "experience_overrides": {
            0: [
                "Lead integrated campaigns and launch work for customer-facing brands, coordinating content, digital, design and production teams through delivery.",
                "Keep brand messaging, timing and execution aligned across physical and digital touchpoints in fast-moving agency environments.",
            ],
            1: [
                "Managed rollout projects in Dubai that blended brand, content and customer experience considerations across digital and on-site applications.",
                "Worked closely with designers, copywriters and production partners to deliver polished campaign assets on schedule.",
            ],
        },
    },
    {
        "company_name": "Nestle",
        "target_role": "Brand Manager",
        "role_badge": "BRAND MANAGER",
        "pdf_title": "Nestle Brand Manager",
        "filename_suffix": "Nestle_BrandManager",
        "tagline": "Shopper Marketing | Rollout | Governance",
        "summary": "Brand Manager with 8+ years of experience supporting integrated marketing, retail activation and brand rollout for consumer-facing businesses. Strong background in brief writing, agency management, campaign planning and brand stewardship across UAE and South African markets. Relevant to FMCG roles that require disciplined execution, cross-functional alignment and brand consistency across shopper and digital channels.",
        "skills": [
            "Brand management",
            "Shopper marketing",
            "Integrated campaign delivery",
            "Retail activation",
            "Agency management",
            "Budget tracking",
            "Launch planning",
            "Brand governance",
            "Stakeholder communication",
            "Performance reporting",
        ],
        "experience_overrides": {
            0: [
                "Lead integrated brand work for UAE clients, taking briefs from strategic input through rollout, launch coordination and stakeholder approvals.",
                "Balance timelines, budgets and cross-functional teams to keep brand execution consistent across digital, retail and campaign touchpoints.",
            ],
            1: [
                "Managed brand development and rollout projects in Dubai, ensuring positioning, messaging and visual execution stayed aligned through delivery.",
                "Partnered with strategy, creative and production teams to move campaigns from brief to market-ready execution.",
            ],
            2: [
                "Project-managed new brand launches across identity, campaign and retail touchpoints, supporting go-to-market readiness and day-to-day client coordination.",
                "Worked across design, copy and production teams to keep brand work commercially grounded and execution-ready.",
            ],
        },
    },
    {
        "company_name": "Hershey",
        "target_role": "Associate Manager Marketing",
        "role_badge": "ASSOCIATE MANAGER MARKETING",
        "pdf_title": "Hershey Associate Manager Marketing",
        "filename_suffix": "Hershey_AssociateMarketManager",
        "tagline": "Regional Delivery | Planning | Reporting",
        "summary": "Marketing Manager with 8+ years of experience coordinating integrated campaigns, launch activity and cross-functional delivery across agency teams in the UAE and South Africa. Strong grounding in media-ready campaign planning, stakeholder management, market execution and performance reporting across digital, retail and activation work. Well suited to MEA marketing roles that require regional coordination, agency management and disciplined delivery against brand and commercial priorities.",
        "skills": [
            "Marketing management",
            "Regional campaign coordination",
            "Integrated marketing",
            "Agency management",
            "Budget planning and tracking",
            "Retail and activation support",
            "Performance reporting",
            "Cross-functional coordination",
            "Market execution",
            "Brand stewardship",
        ],
        "experience_overrides": {
            0: [
                "Lead integrated campaign delivery for UAE clients, coordinating timelines, approvals and cross-functional teams from brief through launch.",
                "Support structured reporting and follow-up so stakeholders have clear visibility on progress, actions and delivery risks.",
            ],
            1: [
                "Managed campaign and rollout plans in Dubai, aligning strategy, creative, design and production teams around launch deadlines and execution quality.",
                "Built practical workback schedules and approval checkpoints to keep fast-moving projects on track.",
            ],
        },
    },
    {
        "company_name": "Burton",
        "target_role": "Senior Account Manager",
        "role_badge": "SENIOR ACCOUNT MANAGER",
        "pdf_title": "Burton Senior Account Manager",
        "filename_suffix": "Burton_SeniorAccountManager",
        "tagline": "Client Counsel | Campaigns | Team Leadership",
        "summary": "Senior Account Manager with 8+ years of experience leading integrated campaigns, stakeholder relationships and cross-functional delivery for regional and global agency clients. Strong background in client counsel, briefing, content development, reporting and issue management across brand, digital and campaign work. Well suited to agency roles that require senior client handling, structured account leadership and high service standards.",
        "skills": [
            "Senior account management",
            "Client counsel and communication",
            "Integrated campaign planning",
            "Stakeholder management",
            "Content development",
            "Reporting and measurement",
            "Issue and escalation management",
            "Budget and timeline control",
            "Cross-functional leadership",
            "Agency service delivery",
        ],
        "experience_overrides": {
            0: [
                "Lead senior client relationships across multiple accounts, setting delivery priorities, shaping responses and keeping cross-functional teams aligned.",
                "Provide structured status updates, recommendations and issue escalation management while protecting scope, budgets and deadlines.",
            ],
            1: [
                "Managed complex day-to-day agency accounts in Dubai, acting as the link between client stakeholders and internal strategy, creative and production teams.",
                "Turned briefs into clear delivery plans and kept workstreams moving through approvals, revisions and launch.",
            ],
        },
    },
    {
        "company_name": "Burson",
        "target_role": "Senior Account Manager",
        "role_badge": "SENIOR ACCOUNT MANAGER",
        "pdf_title": "Burson Senior Account Manager",
        "filename_suffix": "Burson_SeniorAccountManager",
        "tagline": "Client Counsel | Campaigns | Team Leadership",
        "summary": "Senior Account Manager with 8+ years of experience leading integrated campaigns, stakeholder relationships and cross-functional delivery for regional and global agency clients. Strong background in client counsel, briefing, content development, reporting and issue management across brand, digital and campaign work. Well suited to communications and advisory roles that require senior client handling, structured account leadership and high service standards.",
        "skills": [
            "Senior account management",
            "Client counsel and communication",
            "Integrated campaign planning",
            "Stakeholder management",
            "Content development",
            "Reporting and measurement",
            "Issue and escalation management",
            "Budget and timeline control",
            "Cross-functional leadership",
            "Agency service delivery",
        ],
        "experience_overrides": {
            0: [
                "Lead senior client relationships across multiple accounts, setting delivery priorities, shaping responses and keeping cross-functional teams aligned.",
                "Provide structured status updates, recommendations and issue escalation management while protecting scope, budgets and deadlines.",
            ],
            1: [
                "Managed complex day-to-day agency accounts in Dubai, acting as the link between client stakeholders and internal strategy, creative and production teams.",
                "Turned briefs into clear delivery plans and kept workstreams moving through approvals, revisions and launch.",
            ],
        },
    },
]


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def sanitize_filename_part(value: str) -> str:
    value = re.sub(r"[/:]+", " - ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def normalize_render_options(options: dict | None = None) -> dict:
    merged = dict(DEFAULT_RENDER_OPTIONS)
    if not options:
        return merged

    design_style = str(options.get("design_style") or merged["design_style"]).strip().lower()
    if design_style in {"signature", "plain"}:
        merged["design_style"] = design_style

    contact_mode = str(options.get("contact_mode") or merged["contact_mode"]).strip().lower()
    if contact_mode in {"full", "minimal"}:
        merged["contact_mode"] = contact_mode

    merged["include_photo"] = coerce_bool(options.get("include_photo"), merged["include_photo"])
    merged["show_highlight_strip"] = coerce_bool(
        options.get("show_highlight_strip"),
        merged["show_highlight_strip"],
    )
    return merged


def build_render_variant_label(options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    labels = [
        "Plain" if resolved["design_style"] == "plain" else "Signature",
        "Photo On" if resolved["include_photo"] else "Photo Off",
        "Full Header" if resolved["contact_mode"] == "full" else "Lean Header",
        "Highlights On" if resolved["show_highlight_strip"] else "Highlights Off",
    ]
    return " | ".join(labels)


def build_render_variant_filename_suffix(options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    parts = []
    if resolved["design_style"] == "plain":
        parts.append("Plain")
    if not resolved["include_photo"]:
        parts.append("No Photo")
    if resolved["contact_mode"] == "minimal":
        parts.append("Lean Header")
    if not resolved["show_highlight_strip"]:
        parts.append("No Highlights")
    return " - ".join(parts)


def build_output_filename(config: dict, options: dict | None = None) -> str:
    company = sanitize_filename_part(config["company_name"])
    role = sanitize_filename_part(config["target_role"])
    variant_suffix = build_render_variant_filename_suffix(options)
    variant_part = f" - {variant_suffix}" if variant_suffix else ""
    return f"{company} - Du-Toit Griesel - {role}{variant_part} - CV.pdf"


def build_contact_line(options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    if resolved["contact_mode"] == "minimal":
        items = [PROFILE["phone"], PROFILE["email"], PROFILE["linkedin"]]
    else:
        items = [PROFILE["location"], PROFILE["phone"], PROFILE["email"], PROFILE["linkedin"]]
    return " | ".join(items)


def build_header_image_html(image_uri: str, options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    if not resolved["include_photo"]:
        return ""
    return (
        f"<img class=\"header-image\" src=\"{escape(image_uri)}\" "
        f"alt=\"{escape(PROFILE['first_name'])} {escape(PROFILE['last_name'])} headshot\">"
    )


def build_experience(config: dict) -> list[dict]:
    experience = copy.deepcopy(BASE_EXPERIENCE)
    for index, bullets in config.get("experience_overrides", {}).items():
        experience[index]["bullets"] = bullets
    return experience


def render_stats(stats: list[dict]) -> str:
    items = []
    for stat in stats:
        items.append(
            "<div class=\"stat\">"
            f"<span class=\"stat-number\">{escape(stat['number'])}</span>"
            f"<span class=\"stat-label\">{escape(stat['label'])}</span>"
            "</div>"
        )
    return "\n".join(items)


def render_stats_section(stats: list[dict], options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    if not resolved["show_highlight_strip"]:
        return ""
    return "<div class=\"stats-row\">\n" + render_stats(stats) + "\n</div>"


def render_skills(skills: list[str]) -> str:
    return "\n".join(f"<div class=\"skill\">{escape(skill)}</div>" for skill in skills)


def render_experience(experience: list[dict]) -> str:
    jobs = []
    for job in experience:
        bullets = "\n".join(f"<li>{escape(bullet)}</li>" for bullet in job["bullets"])
        jobs.append(
            "<article class=\"job\">"
            "<div class=\"job-top\">"
            f"<div class=\"job-title\">{escape(job['title'])}</div>"
            f"<div class=\"job-date\">{escape(job['date'])}</div>"
            "</div>"
            "<div class=\"job-company-line\">"
            f"<span class=\"job-company\">{escape(job['company'])}</span>"
            f"<span class=\"job-location\"> | {escape(job['location'])}</span>"
            "</div>"
            f"<ul class=\"job-bullets\">{bullets}</ul>"
            "</article>"
        )
    return "\n".join(jobs)


def render_education(education: list[dict]) -> str:
    items = []
    for edu in education:
        details_html = ""
        if edu["details"]:
            details_html = f"<div class=\"edu-details\">{escape(edu['details'])}</div>"
        items.append(
            "<div class=\"education-item\">"
            "<div class=\"edu-top\">"
            f"<span class=\"edu-degree\">{escape(edu['degree'])}</span>"
            f"<span class=\"edu-year\">{escape(edu['year'])}</span>"
            "</div>"
            f"<span class=\"edu-school\">{escape(edu['school'])}</span>"
            f"{details_html}"
            "</div>"
        )
    return "\n".join(items)


def get_cv_template_path(options: dict | None = None) -> Path:
    resolved = normalize_render_options(options)
    template_name = "template_plain.html" if resolved["design_style"] == "plain" else "template.html"
    return PROJECT_DIR / template_name


def get_runtime_output_dir() -> Path:
    RUNTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_OUTPUT_DIR


def build_context(config: dict, image_uri: str, options: dict | None = None) -> dict:
    resolved = normalize_render_options(options)
    summary = config["summary"].strip()
    initial = summary[0] if summary else ""
    rest = summary[1:] if len(summary) > 1 else ""
    return {
        "pdf_title": escape(f"Du-Toit Griesel - {config['pdf_title']} - CV"),
        "role_badge": escape(config["role_badge"]),
        "first_name": escape(PROFILE["first_name"]),
        "last_name": escape(PROFILE["last_name"]),
        "tagline": escape(config["tagline"]),
        "contact_line": escape(build_contact_line(resolved)),
        "summary_initial": escape(initial),
        "summary_rest": escape(rest),
        "stats_section_html": render_stats_section(config.get("stats", COMMON_STATS), resolved),
        "skills_html": render_skills(config["skills"]),
        "experience_html": render_experience(build_experience(config)),
        "education_html": render_education(BASE_EDUCATION),
        "footer_title": escape(config["target_role"]),
        "footer_subtitle": escape(PROFILE["footer_subtitle"]),
        "header_image_html": build_header_image_html(image_uri, resolved),
    }


def render_html(template_text: str, context: dict) -> str:
    return Template(template_text).substitute(context)


def chrome_available() -> bool:
    return CHROME_PATH.exists()


def _run_chrome_pdf(temp_html_path: Path, output_pdf_path: Path) -> None:
    command = [
        str(CHROME_PATH),
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--print-to-pdf={output_pdf_path}",
        temp_html_path.resolve().as_uri(),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        if error.stderr:
            raise RuntimeError(f"Chrome PDF error: {error.stderr.strip()}") from error
        raise RuntimeError("Chrome PDF generation failed.") from error


def generate_cv_bytes(config: dict, options: dict | None = None) -> tuple[str, bytes]:
    resolved = normalize_render_options(options)
    filename = build_output_filename(config, resolved)
    chrome_error: RuntimeError | None = None

    if chrome_available():
        template_text = get_cv_template_path(resolved).read_text(encoding="utf-8")
        image_uri = (PROJECT_DIR / "cropped_circle_image.png").resolve().as_uri()
        context = build_context(config, image_uri, resolved)
        html_output = render_html(template_text, context)
        temp_html_path = PROJECT_DIR / f"_build_{slugify(config['filename_suffix'])}.html"
        output_pdf_path = PROJECT_DIR / filename
        temp_html_path.write_text(html_output, encoding="utf-8")

        try:
            _run_chrome_pdf(temp_html_path, output_pdf_path)
            return filename, output_pdf_path.read_bytes()
        except RuntimeError as error:
            chrome_error = error
        finally:
            temp_html_path.unlink(missing_ok=True)
            output_pdf_path.unlink(missing_ok=True)

    try:
        pdf_bytes = build_cv_pdf_bytes(
            profile=PROFILE,
            config=config,
            experience=build_experience(config),
            education=BASE_EDUCATION,
            stats=config.get("stats", COMMON_STATS),
            contact_line=build_contact_line(resolved),
            options=resolved,
            image_path=PROJECT_DIR / "cropped_circle_image.png",
        )
    except RuntimeError as error:
        if chrome_error is not None:
            raise RuntimeError(f"{chrome_error} Fallback renderer also failed: {error}") from error
        raise
    return filename, pdf_bytes


def render_cvs() -> None:
    for config in ROLE_CONFIGS:
        filename, pdf_bytes = generate_cv_bytes(config)
        output_path = PROJECT_DIR / filename
        print(f"Generating {output_path.name}...", end=" ")
        output_path.write_bytes(pdf_bytes)
        print("Success.")


def generate_cv_for_config(config: dict, options: dict | None = None) -> Path:
    """Generate a CV PDF for a single config dict. Returns the output PDF Path."""
    filename, pdf_bytes = generate_cv_bytes(config, options)
    output_pdf_path = get_runtime_output_dir() / filename
    output_pdf_path.write_bytes(pdf_bytes)
    return output_pdf_path


if __name__ == "__main__":
    if not CHROME_PATH.exists():
        print(f"Chrome not found at {CHROME_PATH}; using PDF fallback when available.")
    render_cvs()
