from __future__ import annotations
from flask import Blueprint, jsonify, request, Response
from pathlib import Path


def create_agency_blueprint(orchestrator, store, web_dir: str, maintenance=None):
    bp = Blueprint("agency", __name__)
    page = Path(web_dir) / "agency.html"

    @bp.get("/agency")
    def agency_page():
        if not page.exists():
            return "Interface Agency introuvable", 404
        return Response(page.read_text(encoding="utf-8"), mimetype="text/html")

    @bp.get("/api/agency/status")
    def agency_status():
        missions = store.list(limit=100)
        active = [m for m in missions if m["status"] in
                  ("queued", "planning", "running", "verifying", "retry_wait", "waiting_approval", "paused", "blocked", "interrupted")]
        return jsonify({"ok": True, "active": len(active), "total": len(missions),
                        "max_agents": orchestrator.default_max_agents,
                        "durable": True, "auto_recover": True,
                        "completion_gate": orchestrator.completion_validator is not None,
                        "backups": maintenance.status() if maintenance is not None else {"enabled": False}})


    @bp.get("/api/agency/memory")
    def agency_memory():
        query = request.args.get("q", "")
        limit = request.args.get("limit", "20")
        try:
            limit = int(limit)
        except Exception:
            limit = 20
        return jsonify({"ok": True, "memories": store.search_memory(query, limit)})

    @bp.get("/api/agency/missions")
    def list_missions():
        limit = request.args.get("limit", "50")
        try: limit = int(limit)
        except Exception: limit = 50
        return jsonify({"ok": True, "missions": store.list(limit)})

    @bp.post("/api/agency/missions")
    def create_mission():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON invalide"}), 400
        try:
            mission = orchestrator.create(
                goal=data.get("goal", ""),
                max_minutes=data.get("max_minutes", 180),
                max_steps=data.get("max_steps", 12),
                max_agents=data.get("max_agents", orchestrator.default_max_agents),
                metadata={"source": "agency_ui"},
                autostart=data.get("autostart", True) is not False,
                completion_criteria=data.get("completion_criteria", ""),
                continue_until_done=data.get("continue_until_done", True) is not False,
                max_repair_cycles=data.get("max_repair_cycles", 3),
            )
            return jsonify({"ok": True, "mission": mission}), 201
        except (ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @bp.get("/api/agency/missions/<mission_id>")
    def get_mission(mission_id):
        mission = store.get(mission_id)
        if not mission:
            return jsonify({"ok": False, "error": "Mission introuvable"}), 404
        return jsonify({"ok": True, "mission": mission})

    @bp.post("/api/agency/missions/<mission_id>/resume")
    def resume_mission(mission_id):
        try:
            mission = orchestrator.resume(mission_id, "Reprise demandée par l'utilisateur")
            return jsonify({"ok": True, "mission": mission})
        except KeyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 409

    @bp.post("/api/agency/missions/<mission_id>/cancel")
    def cancel_mission(mission_id):
        if not orchestrator.cancel(mission_id):
            return jsonify({"ok": False, "error": "Mission introuvable"}), 404
        return jsonify({"ok": True})

    @bp.delete("/api/agency/missions/<mission_id>")
    def delete_mission(mission_id):
        mission = store.get(mission_id)
        if not mission:
            return jsonify({"ok": False, "error": "Mission introuvable"}), 404
        if mission["status"] not in ("completed", "failed", "cancelled"):
            return jsonify({"ok": False, "error": "Annule ou termine la mission avant suppression"}), 409
        return jsonify({"ok": store.delete(mission_id)})

    return bp
