"""AI task breakdown: paste a project description, get tasks with estimates."""

import os
import json
from flask import Blueprint, request, jsonify

ai_bp = Blueprint("ai_assist", __name__)


@ai_bp.route("/api/ai/breakdown", methods=["POST"])
def ai_breakdown():
    """Break down a project description into tasks with estimates."""
    data = request.get_json()
    description = data.get("description", "")

    if not description:
        return jsonify({"error": "No description provided"}), 400

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        # Fallback: simple rule-based breakdown
        return jsonify({"tasks": _simple_breakdown(description), "source": "heuristic"})

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f"""Break down this project description into actionable tasks.
For each task provide: title, description, estimated hours, priority (low/medium/high/urgent), and suggested assignee role.
Return as JSON array of objects.

Project description:
{description}

Return ONLY a JSON array, no other text."""

        response = client.chat.completions.create(
            model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()
        # Parse JSON from response
        import re
        text = re.sub(r"```json?\s*", "", text)
        text = re.sub(r"```", "", text)
        tasks = json.loads(text)

        # Normalize task format
        normalized = []
        for t in tasks:
            normalized.append({
                "title": t.get("title", "Untitled"),
                "description": t.get("description", ""),
                "estimated_hours": t.get("estimated_hours", t.get("hours", 1)),
                "priority": t.get("priority", "medium"),
                "assignee": t.get("assignee", t.get("suggested_assignee_role", "")),
            })

        return jsonify({"tasks": normalized, "source": "ai"})

    except Exception as e:
        return jsonify({
            "tasks": _simple_breakdown(description),
            "source": "heuristic",
            "ai_error": str(e)
        })


@ai_bp.route("/api/ai/suggest", methods=["POST"])
def ai_suggest():
    """Suggest next steps for a task."""
    data = request.get_json()
    task_title = data.get("title", "")
    task_description = data.get("description", "")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"suggestions": ["Break into subtasks", "Define acceptance criteria", "Set a deadline"]})

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": f"Suggest 3-5 actionable next steps for this task:\nTitle: {task_title}\nDescription: {task_description}\n\nReturn as JSON array of strings."}],
            max_tokens=500,
            temperature=0.5,
        )

        text = response.choices[0].message.content.strip()
        import re
        text = re.sub(r"```json?\s*", "", text)
        text = re.sub(r"```", "", text)
        suggestions = json.loads(text)
        return jsonify({"suggestions": suggestions})

    except Exception as e:
        return jsonify({"suggestions": ["Break into subtasks", "Define acceptance criteria", "Set a deadline"], "error": str(e)})


def _simple_breakdown(description: str) -> list:
    """Simple heuristic task breakdown when AI is unavailable."""
    lines = [l.strip() for l in description.split("\n") if l.strip()]
    tasks = []

    for i, line in enumerate(lines):
        # Skip very short lines or headers
        if len(line) < 10:
            continue
        # Detect bullet points or numbered items
        clean = line.lstrip("-*0123456789.) ")
        if clean:
            tasks.append({
                "title": clean[:80],
                "description": line,
                "estimated_hours": 2,
                "priority": "medium",
                "assignee": "",
            })

    # If no bullet points found, create generic phases
    if not tasks:
        phases = ["Research and Planning", "Design", "Implementation", "Testing", "Deployment"]
        for phase in phases:
            tasks.append({
                "title": f"{phase}: {description[:50]}",
                "description": f"{phase} phase for: {description[:200]}",
                "estimated_hours": 4,
                "priority": "medium",
                "assignee": "",
            })

    return tasks[:20]
