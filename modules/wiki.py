"""Wiki module: create/edit pages in Markdown with tree navigation and search."""

from flask import Blueprint, request, jsonify, render_template
import markdown as md
from storage import (
    get_wiki_pages, get_wiki_page, create_wiki_page,
    update_wiki_page, delete_wiki_page, search_wiki
)

wiki_bp = Blueprint("wiki", __name__)


@wiki_bp.route("/wiki")
def wiki_index():
    pages = get_wiki_pages()
    return render_template("wiki.html", pages=pages, current_page=None)


@wiki_bp.route("/wiki/<slug>")
def wiki_page(slug):
    page = get_wiki_page(slug)
    if not page:
        return "Page not found", 404
    pages = get_wiki_pages()
    content_html = md.markdown(
        page["content"],
        extensions=["fenced_code", "tables", "toc", "nl2br"]
    )
    return render_template("wiki.html", pages=pages, current_page=page,
                           content_html=content_html)


@wiki_bp.route("/wiki/<slug>/edit")
def wiki_edit(slug):
    page = get_wiki_page(slug)
    if not page:
        return "Page not found", 404
    pages = get_wiki_pages()
    return render_template("wiki.html", pages=pages, current_page=page, editing=True)


@wiki_bp.route("/api/wiki", methods=["GET"])
def api_list_pages():
    return jsonify(get_wiki_pages())


@wiki_bp.route("/api/wiki/<slug>", methods=["GET"])
def api_get_page(slug):
    page = get_wiki_page(slug)
    if not page:
        return jsonify({"error": "Not found"}), 404
    return jsonify(page)


@wiki_bp.route("/api/wiki", methods=["POST"])
def api_create_page():
    data = request.get_json()
    result = create_wiki_page(
        title=data.get("title", "Untitled"),
        content=data.get("content", ""),
        parent_id=data.get("parent_id"),
    )
    return jsonify(result), 201


@wiki_bp.route("/api/wiki/<slug>", methods=["PUT"])
def api_update_page(slug):
    data = request.get_json()
    ok = update_wiki_page(
        slug=slug,
        title=data.get("title"),
        content=data.get("content"),
    )
    if not ok:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ok": True})


@wiki_bp.route("/api/wiki/<slug>", methods=["DELETE"])
def api_delete_page(slug):
    ok = delete_wiki_page(slug)
    if not ok:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ok": True})


@wiki_bp.route("/api/wiki/search", methods=["GET"])
def api_search_wiki():
    q = request.args.get("q", "")
    if not q:
        return jsonify([])
    return jsonify(search_wiki(q))
