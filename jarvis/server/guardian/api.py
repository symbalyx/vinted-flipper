"""
Blueprint Flask du Gardien. Toutes les routes sont servies sous /api/guardian/*
et héritent de l'authentification globale de JARVIS (cf. before_request).

Le navigateur ne parle qu'à cette API authentifiée : aucune clé n'est exposée.
"""

import logging
from pathlib import Path

from flask import Blueprint, request, jsonify, Response

from .legal_osint import validate_legal_osint_context

logger = logging.getLogger("JARVIS.guardian.api")


def create_guardian_blueprint(service, perms=None, emergency_approval=None,
                              realtime_provider=None, pairing=None, geolocator=None,
                              web_dir=None):
    bp = Blueprint("guardian", __name__)
    web_dir = Path(web_dir) if web_dir else None

    @bp.route("/gardien")
    def gardien_page():
        if not web_dir:
            return "Interface Gardien introuvable.", 404
        f = web_dir / "gardien.html"
        if not f.exists():
            return "gardien.html introuvable.", 404
        return Response(f.read_text(encoding="utf-8"), mimetype="text/html")

    @bp.route("/api/guardian/status")
    def status():
        return jsonify(service.status())

    @bp.route("/api/guardian/enable", methods=["POST"])
    def enable():
        body = request.get_json(silent=True) or {}
        return jsonify({"enabled": service.set_enabled(bool(body.get("on", True)))})

    @bp.route("/api/guardian/arm", methods=["POST"])
    def arm():
        body = request.get_json(silent=True) or {}
        return jsonify({"armed": service.set_armed(bool(body.get("on", False)))})

    @bp.route("/api/guardian/analyze", methods=["POST"])
    def analyze():
        body = request.get_json(silent=True) or {}
        image = body.get("image", "")
        if not isinstance(image, str) or not image:
            return jsonify({"ok": False, "error": "image manquante"}), 400
        meta = body.get("meta", {}) if isinstance(body.get("meta"), dict) else {}
        result = service.process_image(image, meta)
        code = 200 if result.get("ok") else 429 if "rate" in result.get("error", "") else 400
        return jsonify(result), code

    @bp.route("/api/guardian/siren", methods=["POST"])
    def siren():
        body = request.get_json(silent=True) or {}
        action = body.get("action", "start")
        if action == "stop":
            if service.siren:
                try:
                    service.siren("stop")
                except Exception:
                    pass
            return jsonify({"ok": True, "message": "Sirène coupée."})
        # Déclenchement manuel = autorisé par la politique (manual_trigger).
        return jsonify(service.trigger_siren(source="manuel",
                                             approval_facts={"manual_trigger": True}))

    @bp.route("/api/guardian/geolocate", methods=["POST"])
    def geolocate_photo():
        """Photo → coordonnées. EXIF d'abord, estimation visuelle sinon.

        L'image n'est pas sauvegardée. Une estimation visuelle est toujours
        marquée exact=false et peut renvoyer plusieurs candidats.
        """
        if not geolocator:
            return jsonify({"ok": False, "error": "Géolocalisation indisponible"}), 503
        body = request.get_json(silent=True) or {}
        image = body.get("image", "")
        if not isinstance(image, str) or not image:
            return jsonify({"ok": False, "error": "image manquante"}), 400
        context, error, status_code = validate_legal_osint_context(body)
        if not context:
            return jsonify({"ok": False, "error": error, "status": "policy_denied"}), status_code
        hint = body.get("hint", "") if isinstance(body.get("hint", ""), str) else ""
        result = geolocator.locate(image, hint=hint, context=context)
        if result.get("ok"):
            result["legal_scope"] = {
                "purpose": context.purpose,
                "target_type": context.target_type,
                "person_identification": False,
                "private_address_lookup": False,
            }
            return jsonify(result)
        code = 429 if result.get("status") == "rate_limited" else 400
        return jsonify(result), code

    @bp.route("/api/guardian/events")
    def events():
        if not service.store:
            return jsonify({"events": []})
        return jsonify({"events": service.store.recent_events(50),
                        "decisions": service.store.recent_decisions(50)})

    @bp.route("/api/guardian/export")
    def export():
        if not service.store:
            return jsonify({})
        return jsonify(service.store.export())

    @bp.route("/api/guardian/wipe", methods=["POST"])
    def wipe():
        if service.store:
            service.store.wipe()
        return jsonify({"ok": True, "message": "Données Gardien effacées."})

    # ── Temps réel : mint d'un jeton éphémère côté serveur ─────
    @bp.route("/api/guardian/realtime/session", methods=["POST"])
    def realtime_session():
        if not service.cfg.audio_enabled:
            return jsonify({"ok": False, "error": "Audio désactivé (GUARDIAN_AUDIO_ENABLED=0)."}), 403
        if not realtime_provider:
            return jsonify({"ok": False, "error": "Aucun fournisseur temps réel configuré."}), 400
        try:
            return jsonify({"ok": True, **realtime_provider.mint_ephemeral_session()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 502

    # ── Approbation d'urgence ──────────────────────────────────
    @bp.route("/api/guardian/emergency/request", methods=["POST"])
    def emergency_request():
        if not emergency_approval:
            return jsonify({"ok": False, "error": "Indisponible"}), 400
        body = request.get_json(silent=True) or {}
        return jsonify(emergency_approval.request_call(
            target=body.get("target", "owner"), reason=body.get("reason", "")))

    @bp.route("/api/guardian/emergency/confirm", methods=["POST"])
    def emergency_confirm():
        if not emergency_approval:
            return jsonify({"ok": False, "error": "Indisponible"}), 400
        body = request.get_json(silent=True) or {}
        token = body.get("approval_id", "")
        if not token:
            return jsonify({"ok": False, "message": "approval_id requis"}), 400
        return jsonify(emergency_approval.confirm_call(
            token, target=body.get("target", "owner"), reason=body.get("reason", "")))

    # ── Appairage téléphone/tablette ───────────────────────────
    @bp.route("/api/guardian/pair/create", methods=["POST"])
    def pair_create():
        if not pairing:
            return jsonify({"ok": False, "error": "Indisponible"}), 400
        body = request.get_json(silent=True) or {}
        return jsonify(pairing.create_code(name=body.get("name", "Appareil Gardien")))

    @bp.route("/api/guardian/pair/redeem", methods=["POST"])
    def pair_redeem():
        if not pairing:
            return jsonify({"ok": False, "error": "Indisponible"}), 400
        body = request.get_json(silent=True) or {}
        return jsonify(pairing.redeem(body.get("code", ""), body.get("device_name", "")))

    @bp.route("/api/guardian/pair/devices")
    def pair_devices():
        if not pairing:
            return jsonify({"devices": []})
        return jsonify({"devices": pairing.list_devices()})

    @bp.route("/api/guardian/pair/revoke", methods=["POST"])
    def pair_revoke():
        if not pairing:
            return jsonify({"ok": False, "error": "Indisponible"}), 400
        body = request.get_json(silent=True) or {}
        return jsonify({"ok": pairing.revoke(body.get("device_id", ""))})

    return bp
