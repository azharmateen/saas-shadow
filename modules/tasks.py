"""Task tracker module: CRUD API routes with filters and sorting."""

from flask import Blueprint, request, jsonify, render_template
from storage import get_tasks, get_task, create_task, update_task, delete_task

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/tasks")
def tasks_page():
    status = request.args.get("status")
    priority = request.args.get("priority")
    tasks = get_tasks(status=status, priority=priority)
    return render_template("tasks.html", tasks=tasks)


@tasks_bp.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    tasks = get_tasks(
        status=request.args.get("status"),
        priority=request.args.get("priority"),
        assignee=request.args.get("assignee"),
        sort_by=request.args.get("sort", "created_at"),
    )
    return jsonify(tasks)


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["GET"])
def api_get_task(task_id):
    task = get_task(task_id)
    if not task:
        return jsonify({"error": "Not found"}), 404
    return jsonify(task)


@tasks_bp.route("/api/tasks", methods=["POST"])
def api_create_task():
    data = request.get_json()
    task_id = create_task(
        title=data.get("title", "Untitled"),
        description=data.get("description", ""),
        assignee=data.get("assignee", ""),
        due_date=data.get("due_date", ""),
        priority=data.get("priority", "medium"),
        status=data.get("status", "open"),
        tags=data.get("tags", []),
    )
    return jsonify({"id": task_id}), 201


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
def api_update_task(task_id):
    data = request.get_json()
    update_task(task_id, **data)
    return jsonify({"ok": True})


@tasks_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    delete_task(task_id)
    return jsonify({"ok": True})
