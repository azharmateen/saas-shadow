"""Kanban board module: CRUD API routes for cards and columns."""

from flask import Blueprint, request, jsonify, render_template
from storage import get_board, create_card, move_card, delete_card, update_card

kanban_bp = Blueprint("kanban", __name__)


@kanban_bp.route("/kanban")
def kanban_page():
    board = get_board(1)
    return render_template("kanban.html", board=board)


@kanban_bp.route("/api/board", methods=["GET"])
@kanban_bp.route("/api/board/<int:board_id>", methods=["GET"])
def api_get_board(board_id=1):
    board = get_board(board_id)
    return jsonify(board)


@kanban_bp.route("/api/cards", methods=["POST"])
def api_create_card():
    data = request.get_json()
    card_id = create_card(
        title=data.get("title", "Untitled"),
        column=data.get("column", "Todo"),
        board_id=data.get("board_id", 1),
        description=data.get("description", ""),
        color=data.get("color", ""),
    )
    return jsonify({"id": card_id}), 201


@kanban_bp.route("/api/cards/<int:card_id>", methods=["PUT"])
def api_update_card(card_id):
    data = request.get_json()
    update_card(card_id, **data)
    return jsonify({"ok": True})


@kanban_bp.route("/api/cards/<int:card_id>/move", methods=["POST"])
def api_move_card(card_id):
    data = request.get_json()
    move_card(card_id, data["column"], data.get("position", 0))
    return jsonify({"ok": True})


@kanban_bp.route("/api/cards/<int:card_id>", methods=["DELETE"])
def api_delete_card(card_id):
    delete_card(card_id)
    return jsonify({"ok": True})
