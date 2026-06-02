# ============================================================
# SUMMARIZER
# Sends data to Claude and returns a structured JSON summary.
# Works with both image-based (PDF) and structured (DB/CSV) data.
# ============================================================

import io
import json
import base64
import anthropic

SYSTEM_PROMPT = """You are an operations analyst for Alltech's KY System-2 production line.
You analyze shift data and write concise, accurate summaries for the operations team.
Be direct and specific. Use numbers. Flag real issues — don't soften concerns."""

ANALYSIS_PROMPT = """Analyze this KY System-2 production shift data and return a JSON summary.

Required JSON format (return ONLY valid JSON, no markdown, no preamble):
{
  "headline": "one sentence, max 12 words, states the most important thing about this shift",
  "performance_rating": "on_target" | "attention_needed" | "critical",
  "key_metrics": {
    "bfw_avg": <number or null>,
    "oee_avg": <number or null>,
    "loading_time_avg": <number or null>,
    "bag_hang_success": <number or null>
  },
  "highlights": ["specific positive item with number", "..."],
  "concerns": ["specific issue with number", "..."],
  "recommendation": "one actionable sentence for the next shift operator"
}

Rules:
- highlights and concerns must reference actual numbers from the data
- concerns can be an empty array if everything looks good
- performance_rating is critical only if OEE < 50% or BFW < 60% or a fault mode is active"""


def generate_summary(fetch_result):
    """
    Takes the dict returned by data_fetcher.fetch_latest().
    Returns a parsed dict ready to write to summary.json.
    """
    client = anthropic.Anthropic()

    source_type = fetch_result.get("source_type")

    if source_type == "pdf" and fetch_result.get("raw_images"):
        response_text = _call_with_images(client, fetch_result["raw_images"])
    elif fetch_result.get("structured"):
        response_text = _call_with_structured(client, fetch_result["structured"])
    else:
        raise ValueError("fetch_result has neither raw_images nor structured data")

    try:
        summary = json.loads(response_text)
    except json.JSONDecodeError:
        # Claude occasionally adds a stray character — strip and retry
        clean = response_text.strip().lstrip("```json").rstrip("```").strip()
        summary = json.loads(clean)

    return summary


def _call_with_images(client, pages):
    """Vision path — used for PDF exports."""
    content = []

    for i, page in enumerate(pages):
        buf = io.BytesIO()
        page.save(buf, format="JPEG", quality=85)
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
        })

    content.append({"type": "text", "text": ANALYSIS_PROMPT})

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    return resp.content[0].text


def _call_with_structured(client, structured):
    """Structured data path — used for DB / CSV / API."""
    data_text = json.dumps(structured, indent=2)
    prompt = f"Here is the latest shift data in JSON format:\n\n{data_text}\n\n{ANALYSIS_PROMPT}"

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text
