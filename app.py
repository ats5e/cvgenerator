"""
app.py
Flask web server for DT's AI-powered CV & Cover Letter Generator.
Run with: python app.py
Open:     http://localhost:5050
"""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout, wait
import hashlib
import json
import os
from queue import Empty, Queue
import sys
import time
from pathlib import Path
from threading import Lock
from urllib.parse import quote

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
    persist_runtime_pdf,
    prune_runtime_output_dir,
)

app = Flask(__name__, template_folder=str(PROJECT_DIR / "templates"))
app.config["PROPAGATE_EXCEPTIONS"] = False

AI_CACHE_TTL_SECONDS = int(os.getenv("AI_CACHE_TTL_SECONDS", "1800"))
AI_CACHE_MAX_ENTRIES = int(os.getenv("AI_CACHE_MAX_ENTRIES", "32"))
_ai_cache: dict[str, tuple[float, tuple[dict, dict, list[str]]]] = {}
_ai_cache_lock = Lock()
PDF_CACHE_TTL_SECONDS = int(os.getenv("PDF_CACHE_TTL_SECONDS", "1800"))
PDF_CACHE_MAX_ENTRIES = int(os.getenv("PDF_CACHE_MAX_ENTRIES", "32"))
_pdf_cache: dict[str, tuple[float, dict]] = {}
_pdf_cache_lock = Lock()
STREAM_HEARTBEAT_SECONDS = float(os.getenv("STREAM_HEARTBEAT_SECONDS", "15"))


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
            prune_runtime_output_dir()
            total_started_at = time.perf_counter()
            ai_progress_queue: Queue = Queue()

            # Step 1 — AI analysis
            yield _sse({"status": "analysing", "message": "Analysing job description with AI…"})
            ai_started_at = time.perf_counter()
            with ThreadPoolExecutor(max_workers=1) as executor:
                ai_future = executor.submit(_get_generation, job_description, ai_progress_queue.put)
                (cv_config, cl_content, keywords), cache_hit = yield from _await_future(
                    ai_future,
                    progress_queue=ai_progress_queue,
                )
            ai_seconds = round(time.perf_counter() - ai_started_at, 2)

            if company_override:
                cv_config["company_name"] = company_override
            if role_override:
                cv_config["target_role"] = role_override
                cv_config["role_badge"] = role_override.upper()
            if recipient_override:
                cl_content["recipient"] = recipient_override

            yield _sse({
                "status": "keywords",
                "message": (
                    f"Reused cached AI analysis and extracted {len(keywords)} ATS keywords"
                    if cache_hit else
                    f"Extracted {len(keywords)} ATS keywords"
                ),
                "keywords": keywords,
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
                "recipient": cl_content.get("recipient", "Dear Hiring Team,"),
                "render_options": render_options,
                "variant_label": build_render_variant_label(render_options),
                "cache_hit": cache_hit,
                "ai_seconds": ai_seconds,
            })

            # Step 2 — PDF rendering
            render_cache_key = _render_cache_key(cv_config, cl_content, render_options)
            cached_render = _get_cached_render(render_cache_key)

            if cached_render is not None:
                yield _sse({"status": "cv", "message": "Reusing cached CV PDF…"})
                yield _sse({"status": "letter", "message": "Reusing cached cover letter PDF…"})
                cv_filename = cached_render["cv_filename"]
                letter_filename = cached_render["letter_filename"]
                cv_url = _download_url(cached_render["cv_storage_name"], cv_filename)
                letter_url = _download_url(cached_render["letter_storage_name"], letter_filename)
                pdf_seconds = 0.0
                pdf_cache_hit = True
            else:
                yield _sse({"status": "cv", "message": "Generating tailored CV PDF…"})
                yield _sse({"status": "letter", "message": "Generating tailored cover letter PDF…"})
                pdf_started_at = time.perf_counter()
                with ThreadPoolExecutor(max_workers=2) as executor:
                    cv_future = executor.submit(generate_cv_bytes, cv_config, render_options)
                    letter_future = executor.submit(
                        generate_cover_letter_bytes,
                        cv_config,
                        cl_content,
                        render_options,
                    )
                    yield from _await_futures([cv_future, letter_future])
                    cv_filename, cv_bytes = cv_future.result()
                    letter_filename, letter_bytes = letter_future.result()
                pdf_seconds = round(time.perf_counter() - pdf_started_at, 2)

                cv_stored_path = persist_runtime_pdf(cv_filename, cv_bytes)
                cv_url = _download_url(cv_stored_path.name, cv_filename)
                letter_stored_path = persist_runtime_pdf(letter_filename, letter_bytes)
                letter_url = _download_url(letter_stored_path.name, letter_filename)
                _store_cached_render(
                    render_cache_key,
                    {
                        "cv_filename": cv_filename,
                        "letter_filename": letter_filename,
                        "cv_storage_name": cv_stored_path.name,
                        "letter_storage_name": letter_stored_path.name,
                    },
                )
                pdf_cache_hit = False

            # Step 3 — Done
            yield _sse({
                "status": "done",
                "message": "Both documents ready.",
                "cv_filename": cv_filename,
                "letter_filename": letter_filename,
                "cv_url": cv_url,
                "letter_url": letter_url,
                "company": cv_config["company_name"],
                "role": cv_config["target_role"],
                "recipient": cl_content.get("recipient", "Dear Hiring Team,"),
                "keywords": keywords,
                "render_options": render_options,
                "variant_label": build_render_variant_label(render_options),
                "cache_hit": cache_hit,
                "ai_seconds": ai_seconds,
                "pdf_seconds": pdf_seconds,
                "pdf_cache_hit": pdf_cache_hit,
                "total_seconds": round(time.perf_counter() - total_started_at, 2),
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


@app.route("/answer-question", methods=["POST"])
def answer_question():
    data = request.get_json(force=True) or {}
    job_description = (data.get("job_description") or "").strip()
    question = (data.get("question") or "").strip()
    company_name = (data.get("company_name") or "").strip()
    role_title = (data.get("role_title") or "").strip()

    if not job_description:
        return jsonify({"error": "Paste a job description first — the AI needs it to tailor the answer."}), 400
    if not question:
        return jsonify({"error": "No question provided."}), 400

    try:
        answer = ai_engine.answer_question(
            job_description=job_description,
            question=question,
            company_name=company_name,
            role_title=role_title,
        )
        return jsonify({"answer": answer})
    except Exception as error:  # noqa: BLE001
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": _friendly_error_message(error)}), 500


@app.route("/download/<path:filename>")
def download(filename: str):
    # Prevent path traversal
    safe = get_runtime_output_dir() / Path(filename).name
    if safe.suffix.lower() != ".pdf" or not safe.exists():
        return jsonify({"error": "File not found."}), 404
    download_name = Path((request.args.get("name") or safe.name)).name
    return send_file(safe, as_attachment=True, download_name=download_name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _sse_comment(comment: str = "keepalive") -> str:
    return f": {comment}\n\n"


def _job_cache_key(job_description: str) -> str:
    normalized = " ".join(job_description.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _download_url(storage_name: str, download_name: str) -> str:
    return f"/download/{quote(storage_name)}?name={quote(download_name)}"


def _prune_ai_cache(now: float | None = None) -> None:
    current = now if now is not None else time.time()
    expired = [
        key for key, (created_at, _payload) in _ai_cache.items()
        if current - created_at > AI_CACHE_TTL_SECONDS
    ]
    for key in expired:
        _ai_cache.pop(key, None)

    while len(_ai_cache) > AI_CACHE_MAX_ENTRIES:
        oldest_key = min(_ai_cache, key=lambda item: _ai_cache[item][0])
        _ai_cache.pop(oldest_key, None)


def _get_generation(
    job_description: str,
    progress_callback=None,
) -> tuple[tuple[dict, dict, list[str]], bool]:
    key = _job_cache_key(job_description)
    now = time.time()

    with _ai_cache_lock:
        _prune_ai_cache(now)
        cached = _ai_cache.get(key)
        if cached is not None:
            created_at, payload = cached
            if now - created_at <= AI_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload), True

    payload = ai_engine.generate_config(job_description, progress_callback=progress_callback)

    with _ai_cache_lock:
        _ai_cache[key] = (time.time(), copy.deepcopy(payload))
        _prune_ai_cache()

    return copy.deepcopy(payload), False


def _render_cache_key(cv_config: dict, cl_content: dict, render_options: dict) -> str:
    payload = {
        "cv_config": cv_config,
        "cl_content": cl_content,
        "render_options": render_options,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _prune_pdf_cache(now: float | None = None) -> None:
    current = now if now is not None else time.time()
    expired = [
        key for key, (created_at, payload) in _pdf_cache.items()
        if current - created_at > PDF_CACHE_TTL_SECONDS
        or not (get_runtime_output_dir() / payload["cv_storage_name"]).exists()
        or not (get_runtime_output_dir() / payload["letter_storage_name"]).exists()
    ]
    for key in expired:
        _pdf_cache.pop(key, None)

    while len(_pdf_cache) > PDF_CACHE_MAX_ENTRIES:
        oldest_key = min(_pdf_cache, key=lambda item: _pdf_cache[item][0])
        _pdf_cache.pop(oldest_key, None)


def _get_cached_render(render_key: str) -> dict | None:
    now = time.time()
    with _pdf_cache_lock:
        _prune_pdf_cache(now)
        cached = _pdf_cache.get(render_key)
        if cached is None:
            return None
        created_at, payload = cached
        if now - created_at > PDF_CACHE_TTL_SECONDS:
            _pdf_cache.pop(render_key, None)
            return None
        return dict(payload)


def _store_cached_render(render_key: str, payload: dict) -> None:
    with _pdf_cache_lock:
        _pdf_cache[render_key] = (time.time(), dict(payload))
        _prune_pdf_cache()


def _drain_progress_events(progress_queue: Queue | None) -> list[str]:
    if progress_queue is None:
        return []
    events = []
    while True:
        try:
            payload = progress_queue.get_nowait()
        except Empty:
            break
        events.append(_sse(payload))
    return events


def _await_future(future, progress_queue: Queue | None = None):
    while True:
        try:
            result = future.result(timeout=STREAM_HEARTBEAT_SECONDS)
            for event in _drain_progress_events(progress_queue):
                yield event
            return result
        except FutureTimeout:
            events = _drain_progress_events(progress_queue)
            if events:
                for event in events:
                    yield event
            else:
                yield _sse_comment()


def _await_futures(futures: list) -> None:
    pending = set(futures)
    while pending:
        done, pending = wait(pending, timeout=STREAM_HEARTBEAT_SECONDS)
        if pending:
            yield _sse_comment()


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
    if "chrome pdf rendering timed out" in lowered:
        return "PDF rendering took too long on the server."
    if "chrome pdf error" in lowered:
        return "PDF rendering failed on the server."

    return raw[:220]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY not found in .env")
    port = int(os.getenv("PORT", "5050"))
    host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    print(f"🚀  DT's CV Generator → http://{host}:{port}")
    app.run(debug=False, host=host, port=port, threaded=True)
