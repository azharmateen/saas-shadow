"""Flask app: serves the kanban board, task tracker, and wiki."""

import os
import yaml
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

from storage import init_db, set_db_path
from modules.kanban import kanban_bp
from modules.tasks import tasks_bp
from modules.wiki import wiki_bp
from modules.ai_assist import ai_bp

# Load config
config_path = os.environ.get("CONFIG_PATH", "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "saas-shadow-dev-key")

# Set database path from config
db_path = config.get("database", {}).get("path", "./saas_shadow.db")
set_db_path(db_path)
init_db()

# Register modules based on config
modules_config = config.get("modules", {})
if modules_config.get("kanban", True):
    app.register_blueprint(kanban_bp)
if modules_config.get("tasks", True):
    app.register_blueprint(tasks_bp)
if modules_config.get("wiki", True):
    app.register_blueprint(wiki_bp)

# Always register AI assist
app.register_blueprint(ai_bp)

# Make config available to templates
@app.context_processor
def inject_config():
    return {
        "project_config": config,
        "project_name": config.get("project", {}).get("name", "saas-shadow"),
        "theme_default": config.get("theme", {}).get("default", "dark"),
        "accent_color": config.get("theme", {}).get("accent", "#58a6ff"),
        "modules_enabled": modules_config,
    }


@app.route("/")
def index():
    # Redirect to first enabled module
    if modules_config.get("kanban", True):
        return redirect(url_for("kanban.kanban_page"))
    elif modules_config.get("tasks", True):
        return redirect(url_for("tasks.tasks_page"))
    elif modules_config.get("wiki", True):
        return redirect(url_for("wiki.wiki_index"))
    return "No modules enabled. Edit config.yaml."


if __name__ == "__main__":
    host = config.get("server", {}).get("host", "0.0.0.0")
    port = config.get("server", {}).get("port", 5678)
    debug = config.get("server", {}).get("debug", True)
    project_name = config.get("project", {}).get("name", "saas-shadow")
    print(f"  {project_name} running at http://localhost:{port}")
    app.run(host=host, port=port, debug=debug)
