"""
app.py
Flask web server for DT's AI-powered CV & Cover Letter Generator.
Run with: python app.py
Open:     http://localhost:5000
"""
from __future__ import annotations

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
from cover_letter_generator import generate_cover_letter_for_config  # noqa: E402
from generator import generate_cv_for_config  # noqa: E402

app = Flask(__name__, template_folder=str(PROJECT_DIR / "templates"))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True) or {}
    job_description = (data.get("job_description") or "").strip()

    if not job_description:
        return jsonify({"error": "No job description provided."}), 400

    def stream():
        try:
            # Step 1 — AI analysis
            yield _sse({"status": "analysing", "message": "Analysing job description with AI…"})

            cv_config, cl_content, keywords = ai_engine.generate_config(job_description)

            yield _sse({
                "status": "keywords",
                "message": f"Extracted {len(keywords)} ATS keywords",
                "keywords": keywords,
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
            })

            # Step 2 — CV PDF
            yield _sse({"status": "cv", "message": "Generating tailored CV PDF…"})
            cv_path = generate_cv_for_config(cv_config)

            # Step 3 — Cover letter PDF
            yield _sse({"status": "letter", "message": "Generating tailored cover letter PDF…"})
            letter_path = generate_cover_letter_for_config(cv_config, cl_content)

            # Step 4 — Done
            yield _sse({
                "status": "done",
                "message": "Both documents ready.",
                "cv_url": f"/download/{cv_path.name}",
                "letter_url": f"/download/{letter_path.name}",
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
                "keywords": keywords,
            })

        except Exception as exc:  # noqa: BLE001
            import traceback
            yield _sse({"status": "error", "message": str(exc), "detail": traceback.format_exc()})

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
    safe = PROJECT_DIR / Path(filename).name
    if not safe.exists():
        return jsonify({"error": "File not found."}), 404
    return send_file(safe, as_attachment=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not found in .env")
    print("🚀  DT's CV Generator → http://localhost:5050")
    app.run(debug=False, host="127.0.0.1", port=5050, threaded=True)
