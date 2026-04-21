"""
app.py
Flask web server for DT's AI-powered CV & Cover Letter Generator.
Run with: python app.py
Open:     http://localhost:5000
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_file, stream_with_context

load_dotenv(override=True)

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

import ai_engine  # noqa: E402 — must be after sys.path update
from cover_letter_generator import generate_cover_letter_bytes  # noqa: E402
from generator import (  # noqa: E402
    PROFILE,
    build_render_variant_label,
    generate_cv_bytes,
    get_runtime_output_dir,
    normalize_render_options,
)

app = Flask(__name__, template_folder=str(PROJECT_DIR / "templates"))
app.config["PROPAGATE_EXCEPTIONS"] = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", profile=PROFILE)


@app.route("/profile-image")
def profile_image():
    return send_file(PROJECT_DIR / "cropped_circle_image.png", mimetype="image/png")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True) or {}
    job_description = (data.get("job_description") or "").strip()
    recipient_override = (data.get("recipient") or "").strip()
    company_override = (data.get("company_name") or "").strip()
    role_override = (data.get("role_title") or "").strip()
    render_options = normalize_render_options({
        "design_style": data.get("design_style"),
        "include_photo": data.get("include_photo"),
        "contact_mode": data.get("contact_mode"),
        "show_highlight_strip": data.get("show_highlight_strip"),
    })

    if not job_description:
        return jsonify({"error": "No job description provided."}), 400

    def stream():
        try:
            # Step 1 — AI analysis
            yield _sse({"status": "analysing", "message": "Analysing job description with AI…"})

            cv_config, cl_content, keywords = ai_engine.generate_config(job_description)

            if company_override:
                cv_config["company_name"] = company_override
            if role_override:
                cv_config["target_role"] = role_override
                cv_config["role_badge"] = role_override.upper()
            if recipient_override:
                cl_content["recipient"] = recipient_override

            yield _sse({
                "status": "keywords",
                "message": f"Extracted {len(keywords)} ATS keywords",
                "keywords": keywords,
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
                "recipient": cl_content.get("recipient", "Dear Hiring Team,"),
                "render_options": render_options,
                "variant_label": build_render_variant_label(render_options),
            })

            # Step 2 — CV PDF
            yield _sse({"status": "cv", "message": "Generating tailored CV PDF…"})
            cv_filename, cv_bytes = generate_cv_bytes(cv_config, render_options)

            # Step 3 — Cover letter PDF
            yield _sse({"status": "letter", "message": "Generating tailored cover letter PDF…"})
            letter_filename, letter_bytes = generate_cover_letter_bytes(
                cv_config,
                cl_content,
                render_options,
            )

            # Step 4 — Done
            yield _sse({
                "status": "done",
                "message": "Both documents ready.",
                "cv_filename": cv_filename,
                "letter_filename": letter_filename,
                "cv_pdf_base64": base64.b64encode(cv_bytes).decode("ascii"),
                "letter_pdf_base64": base64.b64encode(letter_bytes).decode("ascii"),
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
                "recipient": cl_content.get("recipient", "Dear Hiring Team,"),
                "keywords": keywords,
                "render_options": render_options,
                "variant_label": build_render_variant_label(render_options),
            })

        except Exception as error:  # noqa: BLE001
            import traceback
            print(traceback.format_exc())
            yield _sse({
                "status": "error",
                "message": _friendly_error_message(error),
                "detail": str(error),
            })

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.route("/download/<path:filename>")
def download(filename: str):
    # Prevent path traversal
    safe = get_runtime_output_dir() / Path(filename).name
    if safe.suffix.lower() != ".pdf" or not safe.exists():
        return jsonify({"error": "File not found."}), 404
    return send_file(safe, as_attachment=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _friendly_error_message(error: Exception) -> str:
    raw = str(error).strip() or error.__class__.__name__
    lowered = raw.lower()

    if "openai_api_key not set" in lowered:
        return "OPENAI_API_KEY is not configured on the live server."
    if "api key" in lowered and ("incorrect" in lowered or "invalid" in lowered):
        return "The configured OpenAI API key was rejected."
    if "connection" in lowered and "openai" in lowered:
        return "The server could not reach OpenAI."
    if "chrome pdf rendering is unavailable" in lowered or "fpdf2 is not installed" in lowered:
        return "PDF rendering is not configured correctly for this deployment."
    if "chrome pdf error" in lowered:
        return "PDF rendering failed on the server."

    return raw[:220]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not found in .env")
    print("🚀  DT's CV Generator → http://localhost:5050")
    app.run(debug=False, host="127.0.0.1", port=5050, threaded=True)
