from __future__ import annotations

from datetime import date
from pathlib import Path
from string import Template

from pdf_fallback import build_cover_letter_pdf_bytes
from generator import (
    CHROME_PATH,
    PROFILE,
    PROJECT_DIR,
    ROLE_CONFIGS,
    build_contact_line,
    build_header_image_html,
    build_render_variant_filename_suffix,
    escape,
    get_runtime_output_dir,
    normalize_render_options,
    sanitize_filename_part,
    slugify,
    chrome_available,
)


COVER_LETTER_CONTENT = {
    "Duolingo": {
        "recipient": "Dear Duolingo Hiring Team,",
        "focus": "Localisation, partnerships and regional growth",
        "paragraphs": [
            "I am writing to express my interest in the Regional Marketing Manager, MENA role at Duolingo. With more than eight years of experience leading integrated campaigns, brand rollouts and local market execution across Dubai and South Africa, I would bring a practical mix of regional marketing delivery, stakeholder alignment and culturally aware execution to a role focused on growing brand love in MENA.",
            "In my current role at Yellow Branding & Digital Consultancy in Dubai, I help move work from strategic brief to launch across digital, content and brand touchpoints, coordinating cross-functional teams and keeping senior stakeholders aligned on timelines, messaging and approvals. Earlier roles at HAASXSWITCH, VMLY&R and Ogilvy strengthened my grounding in consumer-facing campaigns, agency management and the discipline required to deliver strong work under pressure and with limited oversight.",
            "What stands out to me about Duolingo is the challenge of making a globally loved brand feel locally resonant. I am particularly drawn to the balance of social, partnerships, PR and growth marketing in this role. My background has taught me how to translate market context into clear briefs, structured execution plans and campaigns that feel relevant to the audience they are meant to reach, while working effectively with distributed teams and multiple decision makers.",
            "I would welcome the opportunity to discuss how my experience in integrated marketing, local market execution and cross-functional delivery could support Duolingo's next phase of growth in MENA. Thank you for your time and consideration.",
        ],
    },
    "Careem": {
        "recipient": "Dear Careem Hiring Team,",
        "focus": "Partner growth, commercial execution and retention",
        "paragraphs": [
            "I am writing to apply for the Key Account Manager role at Careem. Over the past eight years, I have built my career around managing high-touch client relationships, leading complex delivery across multiple teams and keeping commercial priorities moving in fast-paced agency environments in Dubai and Cape Town. That foundation has prepared me well for a role centred on partner growth, performance and long-term relationship management.",
            "At Yellow Branding & Digital Consultancy, I currently manage senior client relationships across multiple accounts, turning business requests into clear workstreams, timelines, approvals and next-step recommendations. My experience has required close attention to service quality, issue resolution, retention and stakeholder communication, while balancing the realities of budgets, delivery pressure and competing priorities.",
            "What appeals to me about Careem is the opportunity to combine relationship management with commercially grounded, data-aware execution. I understand how important it is to align internal teams around growth goals, solve partner pain points quickly and maintain trust while driving better performance. I would bring a calm, accountable approach to account ownership and a strong instinct for keeping momentum across cross-functional teams.",
            "I would be excited to contribute that mindset to Careem's merchant partnerships team in Dubai. Thank you for considering my application.",
        ],
    },
    "General": {
        "recipient": "Dear Hiring Team,",
        "focus": "Premium client experience and relationship building",
        "paragraphs": [
            "I am writing to express my interest in the Client Development Manager opportunity. My background combines more than eight years of account management, premium brand stewardship and omnichannel campaign delivery across Dubai and South Africa, with a strong emphasis on relationship building, execution quality and polished client service.",
            "At Yellow Branding & Digital Consultancy, I have led brand and rollout work across digital, retail and campaign touchpoints, often for clients where presentation quality, consistency and stakeholder confidence are critical. I am comfortable managing multiple moving parts at once, coordinating designers, copywriters, production partners and internal teams while keeping communication clear and standards high.",
            "I would bring a client-first mindset, disciplined follow-through and a strong understanding of how premium brands are experienced across physical and digital moments. My experience has taught me that strong client development depends on detail, trust and relevance, whether the task is a campaign launch, a high-touch brand activation or an ongoing relationship-building programme.",
            "I would welcome the chance to discuss how I could support your team in strengthening client engagement, retention and overall brand experience. Thank you for your time and consideration.",
        ],
    },
    "Dior": {
        "recipient": "Dear Parfums Christian Dior Hiring Team,",
        "focus": "Clienteling, loyalty and omnichannel luxury delivery",
        "paragraphs": [
            "I am writing to express my interest in the Client Development Manager role at Parfums Christian Dior. With more than eight years of experience managing premium-facing brand work across Dubai and South Africa, I have developed a strong appreciation for the detail, consistency and elevated execution required to build meaningful client relationships across channels.",
            "In my current role at Yellow Branding & Digital Consultancy, I lead projects that move from brief through rollout across digital, retail and campaign touchpoints, often with senior stakeholders who expect both strategic thinking and flawless delivery. My earlier experience at Ogilvy, VMLY&R and HAASXSWITCH built a strong foundation in client stewardship, activation planning and coordinating teams around highly considered brand standards.",
            "What attracts me to this opportunity is the chance to help shape client engagement in a more personalised, omnichannel way. I would bring a structured, brand-conscious approach to communication planning, stakeholder alignment and execution, along with the judgement required to maintain luxury standards while supporting retention, loyalty and stronger client lifetime value across markets.",
            "I would welcome the opportunity to discuss how my premium brand experience and delivery discipline could support Dior's client development ambitions in the region. Thank you for your consideration.",
        ],
    },
    "Spotify": {
        "recipient": "Dear Spotify Hiring Team,",
        "focus": "Go-to-market, messaging and digital media storytelling",
        "paragraphs": [
            "I am writing to apply for the Product Marketing Manager, Programmatic role at Spotify. My career has been built around translating complex digital and brand work into clear client-facing narratives, launch plans and well-orchestrated execution, which is why I am excited by the opportunity to support a product marketing function at the intersection of media, technology and commercial storytelling.",
            "From my early years in a digital-led agency to my current work at Yellow Branding & Digital Consultancy in Dubai, I have consistently operated as the bridge between strategy, creative, production and client stakeholders. That has meant turning nuanced briefs into clear propositions, aligning internal teams on deliverables and timelines, and helping campaigns move to market with strong messaging and disciplined follow-through.",
            "What appeals to me about Spotify is the need to make sophisticated advertising capability feel commercially clear, relevant and actionable. I would bring a strong grasp of integrated marketing, a practical go-to-market mindset and the communication discipline to support positioning, sales enablement and performance storytelling in a way that cuts through complexity without losing strategic value.",
            "I would welcome the opportunity to discuss how my background in digital delivery, messaging and cross-functional coordination could support Spotify's programmatic marketing efforts. Thank you for your time and consideration.",
        ],
    },
    "P&G": {
        "recipient": "Dear P&G Hiring Team,",
        "focus": "Brand stewardship, execution and cross-functional delivery",
        "paragraphs": [
            "I am writing to express my interest in the Brand Manager role at P&G. With over eight years of experience managing integrated brand work across Dubai and South Africa, I have developed a strong foundation in brand stewardship, stakeholder alignment, agency coordination and disciplined market execution across digital, retail and campaign environments.",
            "At Yellow Branding & Digital Consultancy, I lead brand projects from strategic input through rollout, working closely with strategy, creative and production teams to ensure positioning, messaging and execution remain aligned. My earlier agency experience gave me a strong grounding in briefs, approvals, launch planning and the detail required to keep work commercially focused while protecting brand consistency.",
            "I am particularly drawn to opportunities where strong brands are built through clarity, consistency and operational discipline. I would bring an agency-trained ability to move fluidly between strategic thinking and hands-on execution, supporting teams with structured planning, clear communication and reliable delivery across multiple stakeholders and workstreams.",
            "I would welcome the opportunity to discuss how my experience could add value to P&G's brand team. Thank you for considering my application.",
        ],
    },
    "Lipton": {
        "recipient": "Dear Lipton Ice Tea Hiring Team,",
        "focus": "Regional brand growth, activation and multi-market rollout",
        "paragraphs": [
            "I am writing to apply for the Brand Manager role at Lipton Ice Tea. The opportunity to support growth across a fast-moving regional business is especially compelling to me, and my background in integrated brand delivery, launch coordination and cross-functional execution across Dubai and South Africa has prepared me well for a role of this nature.",
            "Across Yellow Branding & Digital Consultancy and HAASXSWITCH, I have helped guide brands from strategic brief through launch and rollout, working across digital, retail, campaign and production touchpoints. That experience has sharpened my ability to turn high-level direction into practical toolkits, timelines and deliverables, while keeping multiple stakeholders aligned and maintaining consistency in-market.",
            "I am particularly interested in Lipton's focus on regional deployment, activation and scaling brand growth through local relevance. I would bring strong project leadership, comfort in navigating matrixed teams and a disciplined approach to execution, with the energy and follow-through needed to keep brand initiatives moving across agencies, partners and internal functions.",
            "I would welcome the chance to discuss how my experience could support Lipton's next phase of brand growth and execution across the region. Thank you for your consideration.",
        ],
    },
    "Alabbar": {
        "recipient": "Dear Alabbar Enterprises & ANOTHER Hiring Team,",
        "focus": "F&B brand building, content and guest experience",
        "paragraphs": [
            "I am writing to express my interest in the Brand Marketing Manager role at Alabbar Enterprises & ANOTHER. With more than eight years of experience leading integrated brand work in Dubai and South Africa, including recent work across sectors such as F&B, retail and customer-facing brands, I would bring both creative coordination and disciplined execution to a role focused on brand growth and guest experience.",
            "At Yellow Branding & Digital Consultancy, I have managed projects spanning brand development, rollout and campaign delivery, coordinating designers, copywriters, digital teams and production partners to deliver polished work across physical and digital touchpoints. That experience has required strong judgement, tight organisation and the ability to keep multiple projects moving at once without losing sight of the brand standard or audience experience.",
            "What draws me to this opportunity is the mix of concept development, content, social and on-the-ground brand execution. I enjoy work that sits close to customer experience, and I would bring a practical understanding of how to translate strategy into campaigns, assets and activations that feel relevant, well-crafted and operationally realistic for fast-moving lifestyle and F&B brands.",
            "I would welcome the opportunity to discuss how my background in integrated brand delivery could support Alabbar's portfolio of concepts. Thank you for your time and consideration.",
        ],
    },
    "Nestle": {
        "recipient": "Dear Nestle Hiring Team,",
        "focus": "Shopper marketing, governance and launch execution",
        "paragraphs": [
            "I am writing to apply for the Brand Manager role at Nestle. My agency-side background has given me more than eight years of experience supporting consumer-facing brands through integrated campaign delivery, retail activation, structured rollout and day-to-day stakeholder management across the UAE and South Africa.",
            "In my current role at Yellow Branding & Digital Consultancy, I manage work from briefing through rollout across digital and physical touchpoints, aligning strategy, creative and production teams so delivery remains consistent and commercially grounded. Earlier roles strengthened my ability to write clear briefs, manage approvals and keep brands coherent across multiple channels and fast timelines.",
            "I would bring a strong executional mindset to a role that depends on brand discipline, cross-functional coordination and market-ready delivery. I am comfortable operating in environments where planning, governance and follow-through matter just as much as the creative idea itself, and I understand the importance of keeping agencies and internal teams aligned around a clear brand objective.",
            "I would welcome the opportunity to discuss how my experience could support Nestle's brand ambitions in the region. Thank you for your consideration.",
        ],
    },
    "Hershey": {
        "recipient": "Dear The Hershey Company Hiring Team,",
        "focus": "MEA planning, media coordination and commercial delivery",
        "paragraphs": [
            "I am writing to express my interest in the Associate Manager Marketing MEA role at The Hershey Company. With over eight years of experience coordinating integrated campaigns, launch activity and cross-functional delivery in agency environments, I would bring a strong mix of structured planning, stakeholder management and execution discipline to a role that bridges brand building with commercial focus.",
            "At Yellow Branding & Digital Consultancy in Dubai, I manage projects from brief through launch, aligning strategy, creative, design and production teams while maintaining visibility on timelines, approvals and delivery risks. My experience has also developed my ability to work closely with agency partners, support reporting and keep communications clear across multiple stakeholders and changing priorities.",
            "What attracts me to this role is the balance between brand planning, media coordination and data-informed optimisation. I am comfortable in fast-paced environments where strong organisation, analytical thinking and accountability are essential, and I would bring a reliable, collaborative approach to helping regional teams deliver plans that are both well-executed and commercially grounded.",
            "I would welcome the opportunity to discuss how my background could support Hershey's MEA marketing team. Thank you for your time and consideration.",
        ],
    },
    "Burton": {
        "recipient": "Dear Burton Hiring Team,",
        "focus": "Senior account leadership and integrated delivery",
        "paragraphs": [
            "I am writing to apply for the Senior Account Manager role at Burton. Over the past eight years, I have built my career in agencies where strong client handling, structured project leadership and calm execution are essential, and I would bring that same level of ownership and reliability to your team.",
            "In my current role at Yellow Branding & Digital Consultancy, I lead senior client relationships across multiple accounts, shaping delivery plans, coordinating internal teams and maintaining clear communication from brief to final rollout. Earlier roles at HAASXSWITCH, VMLY&R and Ogilvy gave me a strong grounding in integrated campaigns, issue management, approvals and the practical detail required to keep demanding workstreams on track.",
            "I am particularly well suited to environments that expect both strategic judgement and hands-on account leadership. My approach is to create clarity for clients, keep teams aligned and anticipate risks early so work can move forward with confidence. I value strong service standards and take pride in building trust through consistency, responsiveness and sound follow-through.",
            "I would welcome the chance to discuss how my experience could contribute to Burton's client service offering. Thank you for your consideration.",
        ],
    },
    "Burson": {
        "recipient": "Dear Burson Hiring Team,",
        "focus": "Client counsel, consumer brands and campaign leadership",
        "paragraphs": [
            "I am writing to express my interest in the Senior Account Manager role at Burson. With more than eight years of experience leading integrated account work across consumer-facing brands, I have built a strong foundation in client counsel, content development, stakeholder management and structured delivery in fast-paced agency environments.",
            "At Yellow Branding & Digital Consultancy, I currently manage senior client relationships and coordinate multi-disciplinary teams across branding, digital and campaign projects. My earlier roles at Ogilvy, VMLY&R and HAASXSWITCH taught me how to handle complex feedback, maintain momentum across multiple workstreams and support strong client relationships even under tight timelines and shifting priorities.",
            "What appeals to me about Burson is the opportunity to work where reputation, culture and brand communication intersect. I would bring a thoughtful, commercially aware approach to account leadership, along with the ability to turn briefs into clear plans, keep teams aligned and contribute to work that is strategically grounded and well executed.",
            "I would welcome the opportunity to discuss how my background in integrated client service could support Burson's consumer team. Thank you for your time and consideration.",
        ],
    },
}


def build_cover_letter_filename(config: dict, options: dict | None = None) -> str:
    company = sanitize_filename_part(config["company_name"])
    role = sanitize_filename_part(config["target_role"])
    variant_suffix = build_render_variant_filename_suffix(options)
    variant_part = f" - {variant_suffix}" if variant_suffix else ""
    return f"{company} - Du-Toit Griesel - {role}{variant_part} - Cover Letter.pdf"


def build_letter_date() -> str:
    today = date.today()
    return f"{today.day} {today.strftime('%B %Y')}"


def render_meta(items: list[dict[str, str]]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            "<div class=\"meta-item\">"
            f"<div class=\"meta-label\">{escape(item['label'])}</div>"
            f"<div class=\"meta-value\">{escape(item['value'])}</div>"
            "</div>"
        )
    return "\n".join(blocks)


def render_meta_section(items: list[dict[str, str]], options: dict | None = None) -> str:
    resolved = normalize_render_options(options)
    if not resolved["show_highlight_strip"]:
        return ""
    return "<div class=\"meta-row\">\n" + render_meta(items) + "\n</div>"


def render_letter_body(paragraphs: list[str]) -> str:
    rendered = []
    for index, paragraph in enumerate(paragraphs):
        if index == 0:
            rendered.append(
                "<p>"
                f"<span class=\"drop-cap\">{escape(paragraph[0])}</span>{escape(paragraph[1:])}"
                "</p>"
            )
        else:
            rendered.append(f"<p>{escape(paragraph)}</p>")
    return "\n".join(rendered)


def get_cover_letter_template_path(options: dict | None = None) -> Path:
    resolved = normalize_render_options(options)
    template_name = (
        "cover_letter_template_plain.html"
        if resolved["design_style"] == "plain"
        else "cover_letter_template.html"
    )
    return PROJECT_DIR / template_name


def build_cover_letter_context(config: dict, image_uri: str, options: dict | None = None) -> dict:
    resolved = normalize_render_options(options)
    content = COVER_LETTER_CONTENT[config["company_name"]]
    meta_items = [
        {"label": "Target Company", "value": config["company_name"]},
        {"label": "Opportunity", "value": config["target_role"]},
        {"label": "Focus", "value": content["focus"]},
    ]
    footer_title = f"{config['company_name']} | {config['target_role']}"

    return {
        "pdf_title": escape(f"Du-Toit Griesel - {config['company_name']} - Cover Letter"),
        "first_name": escape(PROFILE["first_name"]),
        "last_name": escape(PROFILE["last_name"]),
        "tagline": escape(config["tagline"]),
        "contact_line": escape(build_contact_line(resolved)),
        "meta_section_html": render_meta_section(meta_items, resolved),
        "letter_date": escape(build_letter_date()),
        "letter_recipient": escape(content["recipient"]),
        "letter_body_html": render_letter_body(content["paragraphs"]),
        "signoff": "Kind regards,",
        "signature_name": escape(f"{PROFILE['first_name']} {PROFILE['last_name']}"),
        "footer_title": escape(footer_title),
        "footer_subtitle": escape(PROFILE["footer_subtitle"]),
        "header_image_html": build_header_image_html(image_uri, resolved),
    }


def render_html(template_text: str, context: dict) -> str:
    return Template(template_text).substitute(context)


def render_pdf(html_output: str, temp_name: str, output_pdf_path: Path) -> None:
    temp_html_path = get_runtime_output_dir() / temp_name
    temp_html_path.write_text(html_output, encoding="utf-8")
    print(f"Generating {output_pdf_path.name}...", end=" ")

    try:
        from generator import _run_chrome_pdf

        _run_chrome_pdf(temp_html_path, output_pdf_path)
        print("Success.")
    except RuntimeError as error:
        print("Failed.")
        print(str(error))
    finally:
        temp_html_path.unlink(missing_ok=True)


def generate_cover_letter_bytes(config: dict, content: dict, options: dict | None = None) -> tuple[str, bytes]:
    resolved = normalize_render_options(options)
    filename = build_cover_letter_filename(config, resolved)
    chrome_error: RuntimeError | None = None

    if chrome_available():
        template_text = get_cover_letter_template_path(resolved).read_text(encoding="utf-8")
        image_uri = (PROJECT_DIR / "cropped_circle_image.png").resolve().as_uri()
        meta_items = [
            {"label": "Target Company", "value": config["company_name"]},
            {"label": "Opportunity", "value": config["target_role"]},
            {"label": "Focus", "value": content.get("focus", "")},
        ]
        footer_title = f"{config['company_name']} | {config['target_role']}"
        context = {
            "pdf_title": escape(f"Du-Toit Griesel - {config['company_name']} - Cover Letter"),
            "first_name": escape(PROFILE["first_name"]),
            "last_name": escape(PROFILE["last_name"]),
            "tagline": escape(config["tagline"]),
            "contact_line": escape(build_contact_line(resolved)),
            "meta_section_html": render_meta_section(meta_items, resolved),
            "letter_date": escape(build_letter_date()),
            "letter_recipient": escape(content.get("recipient", "Dear Hiring Team,")),
            "letter_body_html": render_letter_body(content.get("paragraphs", [])),
            "signoff": "Kind regards,",
            "signature_name": escape(f"{PROFILE['first_name']} {PROFILE['last_name']}"),
            "footer_title": escape(footer_title),
            "footer_subtitle": escape(PROFILE["footer_subtitle"]),
            "header_image_html": build_header_image_html(image_uri, resolved),
        }
        html_output = render_html(template_text, context)
        temp_name = f"_build_cover_letter_{slugify(config['filename_suffix'])}.html"
        temp_html_path = PROJECT_DIR / temp_name
        output_pdf_path = PROJECT_DIR / filename
        temp_html_path.write_text(html_output, encoding="utf-8")
        try:
            from generator import _run_chrome_pdf

            _run_chrome_pdf(temp_html_path, output_pdf_path)
            return filename, output_pdf_path.read_bytes()
        except RuntimeError as error:
            chrome_error = error
        finally:
            temp_html_path.unlink(missing_ok=True)
            output_pdf_path.unlink(missing_ok=True)

    try:
        pdf_bytes = build_cover_letter_pdf_bytes(
            profile=PROFILE,
            config=config,
            content=content,
            contact_line=build_contact_line(resolved),
            letter_date=build_letter_date(),
            options=resolved,
            image_path=PROJECT_DIR / "cropped_circle_image.png",
        )
    except RuntimeError as error:
        if chrome_error is not None:
            raise RuntimeError(f"{chrome_error} Fallback renderer also failed: {error}") from error
        raise
    return filename, pdf_bytes


def render_cover_letters() -> None:
    missing = [
        config["company_name"]
        for config in ROLE_CONFIGS
        if config["company_name"] not in COVER_LETTER_CONTENT
    ]
    if missing:
        raise ValueError(f"Missing cover letter content for: {', '.join(missing)}")

    options = normalize_render_options()
    for config in ROLE_CONFIGS:
        filename, pdf_bytes = generate_cover_letter_bytes(
            config,
            COVER_LETTER_CONTENT[config["company_name"]],
            options,
        )
        output_pdf_path = PROJECT_DIR / filename
        output_pdf_path.write_bytes(pdf_bytes)
        print(f"Generating {output_pdf_path.name}... Success.")


def generate_cover_letter_for_config(config: dict, content: dict, options: dict | None = None) -> Path:
    """
    Generate a cover letter PDF for a single config + content dict.
    content must have keys: recipient (str), focus (str), paragraphs (list[str]).
    Returns the output PDF Path.
    """
    filename, pdf_bytes = generate_cover_letter_bytes(config, content, options)
    output_pdf_path = get_runtime_output_dir() / filename
    output_pdf_path.write_bytes(pdf_bytes)
    return output_pdf_path


if __name__ == "__main__":
    if not CHROME_PATH.exists():
        print(f"Chrome not found at {CHROME_PATH}; using PDF fallback when available.")
    render_cover_letters()
