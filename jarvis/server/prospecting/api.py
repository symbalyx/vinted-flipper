from __future__ import annotations
from flask import Blueprint, jsonify, request, Response
from pathlib import Path


def create_prospecting_blueprint(service, store, web_dir: str, mission_orchestrator=None):
    bp = Blueprint("prospecting", __name__)
    page = Path(web_dir) / "prospection.html"

    @bp.get("/prospection")
    def page_route():
        if not page.exists():
            return "Interface Prospection introuvable", 404
        return Response(page.read_text(encoding="utf-8"), mimetype="text/html")


    @bp.post("/api/prospection/campaigns")
    def create_campaign():
        """Crée une mission Agency de recherche B2B publique, sans envoi automatique."""
        if mission_orchestrator is None:
            return jsonify({"ok": False, "error": "JARVIS Agency indisponible"}), 503
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON invalide"}), 400
        region = str(data.get("region") or "").strip()[:160]
        sector = str(data.get("sector") or "").strip()[:160]
        offer = str(data.get("offer") or "création ou amélioration de site web").strip()[:300]
        prepare_drafts = data.get("prepare_drafts", True) is not False
        try:
            target_count = max(1, min(int(data.get("target_count", 10)), 50))
            max_minutes = max(5, min(int(data.get("max_minutes", 180)), 10080))
            max_agents = max(1, min(int(data.get("max_agents", 4)), 8))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Paramètres numériques invalides"}), 400
        if not region or not sector:
            return jsonify({"ok": False, "error": "Région et secteur requis"}), 400

        draft_instruction = (
            "Prépare un brouillon honnête pour chaque contact professionnel public vérifié, "
            "mais n'envoie aucun message." if prepare_drafts else
            "Ne prépare et n'envoie aucun message ; recherche et qualification uniquement."
        )
        goal = (
            f"Construire dans le CRM JARVIS une campagne de {target_count} prospects B2B "
            f"distincts du secteur « {sector} » dans la zone « {region} » pour l'offre "
            f"« {offer} ». Utilise uniquement des sources professionnelles publiques et "
            "vérifiables. Pour chaque prospect, conserve l'URL source, le site officiel s'il "
            "existe, un contact professionnel public s'il est affiché, les constats factuels, "
            "puis ajoute et qualifie le prospect avec les outils prospection_* de JARVIS. "
            f"{draft_instruction} Respecte la liste d'exclusion, déduplique et ne collecte "
            "aucune adresse privée ni donnée personnelle sensible. Termine par un rapport "
            "chiffré avec les sources, scores, doublons écartés, limites et prochaines actions."
        )
        criteria = (
            f"Le CRM contient au moins {target_count} prospects distincts correspondant à "
            f"« {sector} » et « {region} ». Chaque fiche possède un nom d'entreprise, une URL "
            "source publique accessible, un score et une justification. Les doublons et la "
            "liste d'exclusion ont été vérifiés. " +
            ("Un brouillon non envoyé existe pour chaque prospect disposant d'un e-mail "
             "professionnel public vérifié. " if prepare_drafts else "Aucun brouillon n'est requis. ") +
            "Aucun e-mail n'a été envoyé. Le rapport final donne les comptes exacts et les "
            "éléments non vérifiables sont signalés, jamais inventés."
        )
        mission = mission_orchestrator.create(
            goal, max_minutes=max_minutes, max_steps=24, max_agents=max_agents,
            metadata={"source": "prospecting_campaign", "region": region,
                      "sector": sector, "target_count": target_count,
                      "prepare_drafts": prepare_drafts},
            completion_criteria=criteria, continue_until_done=True,
            max_repair_cycles=5)
        return jsonify({"ok": True, "mission": mission,
                        "agency_url": f"/agency#mission={mission['id']}"}), 201

    @bp.get("/api/prospection/status")
    def status():
        return jsonify({"ok": True, **service.campaign_summary(10)})

    @bp.get("/api/prospection/prospects")
    def list_prospects():
        return jsonify({"ok": True, "prospects": service.list_prospects(
            limit=request.args.get("limit", 100),
            status=request.args.get("status", ""),
            min_score=request.args.get("min_score", 0))})

    @bp.post("/api/prospection/prospects")
    def add_prospect():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON invalide"}), 400
        try:
            prospect = service.add_prospect(**{k: data.get(k) for k in (
                "company_name", "source_url", "website", "public_email", "contact_name",
                "phone", "region", "notes", "source_type", "consent_basis", "tags")})
            return jsonify({"ok": True, "prospect": prospect}), 201
        except (ValueError, PermissionError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @bp.get("/api/prospection/prospects/<prospect_id>")
    def get_prospect(prospect_id):
        p = store.get(prospect_id)
        if not p:
            return jsonify({"ok": False, "error": "Prospect introuvable"}), 404
        p["events"] = store.events(prospect_id)
        p["drafts"] = store.drafts(prospect_id)
        return jsonify({"ok": True, "prospect": p})

    @bp.post("/api/prospection/prospects/<prospect_id>/qualify")
    def qualify(prospect_id):
        try:
            return jsonify({"ok": True, "prospect": service.qualify(prospect_id)})
        except KeyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    @bp.post("/api/prospection/prospects/<prospect_id>/draft")
    def draft(prospect_id):
        data = request.get_json(silent=True) or {}
        try:
            item = service.prepare_message(
                prospect_id, data.get("offer", "création ou amélioration de site web"),
                data.get("sender_name", "Symbalyx"), data.get("demo_url", ""),
                data.get("tone", "professionnel et direct"))
            return jsonify({"ok": True, "draft": item}), 201
        except KeyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        except (ValueError, PermissionError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @bp.post("/api/prospection/prospects/<prospect_id>/suppress")
    def suppress(prospect_id):
        data = request.get_json(silent=True) or {}
        try:
            return jsonify({"ok": True, "prospect": service.suppress(
                prospect_id, data.get("reason", "exclusion manuelle"))})
        except KeyError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404

    return bp
