# CV & Cover Letter Generator

A local web app that turns any job description into a tailored, ATS-optimised CV and cover letter PDF in one click.

- **Frontend**: dark single-page dashboard at `http://localhost:5050`
- **Backend**: Flask + server-sent events
- **AI**: OpenAI `gpt-4o` in JSON mode — extracts ATS keywords, rewrites the summary, skills, experience bullets and cover letter paragraphs to mirror the JD
- **Rendering**: headless Chrome → PDF (print-perfect A4)

## Requirements

- Python 3.9+
- Google Chrome installed at `/Applications/Google Chrome.app` (macOS). Adjust `CHROME_PATH` in `generator.py` for other OSes.
- An OpenAI API key with credit

## Setup

```bash
git clone https://github.com/ats5e/cvgenerator.git
cd cvgenerator

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your OPENAI_API_KEY
```

## Run

```bash
python app.py
```

Open [http://localhost:5050](http://localhost:5050). Paste a job description, click **Generate Application**. Both PDFs are written to the project directory and offered as downloads.

## How it works

1. `POST /generate` receives the JD
2. `ai_engine.py` asks `gpt-4o` to produce a JSON config (role title, ATS keywords, tailored summary, skills, experience overrides, 4 cover letter paragraphs)
3. `generator.py` and `cover_letter_generator.py` render HTML templates populated with that config
4. Chrome prints each to a single-page PDF
5. Download URLs stream back to the frontend via SSE

## Structure

```
app.py                       Flask server + SSE streaming
ai_engine.py                 OpenAI call, JSON schema, candidate context
generator.py                 CV HTML → PDF
cover_letter_generator.py    Cover letter HTML → PDF
template.html                CV template
cover_letter_template.html   Cover letter template
templates/index.html         Frontend SPA
cropped_circle_image.png     Profile photo used by the PDF
```

## Notes

- The port is **5050**, not 5000 — macOS 12+ runs AirPlay Receiver on 5000 by default and intercepts `localhost:5000`.
- Static candidate details (name, phone, email, work history) live in `generator.py` under `PROFILE` and `BASE_EXPERIENCE`. Edit them to personalise.
- The hardcoded `ROLE_CONFIGS` list at the top of `generator.py` is the legacy batch mode — `python generator.py` still renders the full company set without the web UI.
