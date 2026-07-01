"""Service métier de prospection assistée."""
from __future__ import annotations

import os
import time
from .policy import (
    normalize_email, normalize_url, validate_basis,
    validate_public_business_contact, domain_from_email, safe_text,
)


class ProspectingService:
    def __init__(self, store):
        self.store = store
        self.max_sends_per_day = max(1, min(int(os.getenv("PROSPECTING_MAX_SENDS_PER_DAY", "10")), 100))
        self.max_sends_per_domain = max(1, min(int(os.getenv("PROSPECTING_MAX_SENDS_PER_DOMAIN", "2")), 20))
        self.min_send_interval = max(30, min(int(os.getenv("PROSPECTING_MIN_SEND_INTERVAL", "120")), 86400))

    def add_prospect(self, company_name: str, source_url: str, website: str = "",
                     public_email: str = "", contact_name: str = "", phone: str = "",
                     region: str = "", notes: str = "", source_type: str = "official_website",
                     consent_basis: str = "public_b2b", tags=None):
        company_name = safe_text(company_name, 240)
        if len(company_name) < 2:
            raise ValueError("Nom d'entreprise requis")
        source_url = normalize_url(source_url, required=True)
        website = normalize_url(website) if website else ""
        public_email = normalize_email(public_email) if public_email else ""
        basis = validate_basis(consent_basis)
        warnings = validate_public_business_contact(public_email, website, source_url, basis)
        prospect = self.store.add({
            "company_name": company_name,
            "source_url": source_url,
            "website": website,
            "public_email": public_email,
            "contact_name": safe_text(contact_name, 160),
            "phone": safe_text(phone, 80),
            "region": safe_text(region, 160),
            "notes": safe_text(notes, 4000),
            "source_type": safe_text(source_type, 80) or "official_website",
            "consent_basis": basis,
            "tags": [safe_text(t, 60) for t in (tags or [])][:20],
        })
        qualified = self.qualify(prospect["id"])
        qualified["policy_warnings"] = warnings
        return qualified

    def qualify(self, prospect_id: str):
        p = self.store.get(prospect_id)
        if not p:
            raise KeyError("Prospect introuvable")
        score = 0
        reasons = []
        if p.get("source_url"):
            score += 15; reasons.append("source publique enregistrée")
        if p.get("website"):
            score += 10; reasons.append("site officiel identifié")
        else:
            score += 25; reasons.append("absence de site : besoin potentiel à vérifier")
        if p.get("public_email"):
            score += 15; reasons.append("contact professionnel public")
        if p.get("region"):
            score += 8; reasons.append("zone géographique connue")
        notes = (p.get("notes") or "").lower()
        if any(k in notes for k in ("site ancien", "non responsive", "pas de site", "site lent", "erreur", "référencement")):
            score += 17; reasons.append("problème numérique documenté")
        if p.get("consent_basis") in {"existing_relationship", "explicit_consent", "referral"}:
            score += 20; reasons.append("relation ou consentement renforcé")
        if p.get("do_not_contact"):
            score = 0; reasons.append("contact exclu")
        score = min(score, 100)
        status = p.get("status")
        if status == "new":
            status = "qualified" if score >= 45 else "research_needed"
        return self.store.update(
            prospect_id, score=score, score_reason="; ".join(reasons), status=status)

    def list_prospects(self, limit=100, status="", min_score=0):
        return self.store.list(limit, status, min_score)

    def prepare_message(self, prospect_id: str, offer: str = "création ou amélioration de site web",
                        sender_name: str = "Symbalyx", demo_url: str = "",
                        tone: str = "professionnel et direct"):
        p = self.store.get(prospect_id)
        if not p:
            raise KeyError("Prospect introuvable")
        self._assert_contactable(p, require_email=False)
        offer = safe_text(offer, 300)
        sender_name = safe_text(sender_name, 120) or "Symbalyx"
        demo_url = normalize_url(demo_url) if demo_url else ""
        contact = p.get("contact_name") or "Bonjour"
        evidence = []
        if not p.get("website"):
            evidence.append("je n'ai pas trouvé de site officiel clairement accessible depuis votre source publique")
        elif p.get("notes"):
            evidence.append("j'ai relevé quelques pistes d'amélioration sur votre présence en ligne")
        else:
            evidence.append("j'ai consulté votre présence professionnelle publique")
        body = (
            f"{contact},\n\n"
            f"Je me permets de vous contacter car {evidence[0]}. "
            f"Je travaille sur {offer} pour des professionnels et artisans.\n\n"
        )
        if demo_url:
            body += f"J'ai préparé une démonstration consultable ici : {demo_url}\n\n"
        body += (
            "Si le sujet vous intéresse, je peux vous montrer une proposition courte et adaptée, "
            "sans engagement. Quelles seraient vos disponibilités pour un échange de 10 minutes ?\n\n"
            f"Bien cordialement,\n{sender_name}\n\n"
            "Si vous ne souhaitez pas être recontacté, répondez simplement « stop » et je supprimerai vos coordonnées de ma liste."
        )
        subject = f"Une piste pour la présence en ligne de {p['company_name']}"
        draft = self.store.create_draft(prospect_id, subject[:200], body[:12000])
        draft["tone"] = tone
        return draft

    def send_draft(self, draft_id: str, email_service):
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise KeyError("Brouillon introuvable")
        if draft.get("status") == "sent":
            return {"ok": True, "duplicate_prevented": True,
                    "message": "Ce brouillon a déjà été envoyé ; aucun second envoi."}
        p = self.store.get(draft["prospect_id"])
        if not p:
            raise KeyError("Prospect introuvable")
        self._assert_contactable(p, require_email=True)
        self._assert_rate_limits(p["public_email"])
        result = email_service.send(
            p["public_email"], draft["subject"], draft["body"], "")
        self.store.mark_draft_sent(draft_id)
        return result

    def suppress(self, prospect_id: str, reason: str = "opposition ou exclusion manuelle"):
        p = self.store.get(prospect_id)
        if not p:
            raise KeyError("Prospect introuvable")
        email = p.get("public_email", "")
        if email:
            self.store.suppress(email, "email", reason)
            self.store.suppress(domain_from_email(email), "domain", reason)
        self.store.update(prospect_id, do_not_contact=True, status="suppressed")
        self.store.event(prospect_id, "suppressed", reason)
        return self.store.get(prospect_id)

    def mark_reply(self, prospect_id: str, outcome: str, next_followup_at: float | None = None):
        p = self.store.get(prospect_id)
        if not p:
            raise KeyError("Prospect introuvable")
        outcome = safe_text(outcome, 80).lower()
        allowed = {"interested", "not_interested", "later", "no_reply", "meeting_booked", "won", "lost"}
        if outcome not in allowed:
            raise ValueError("Résultat de contact invalide")
        if outcome == "not_interested":
            return self.suppress(prospect_id, "prospect non intéressé")
        self.store.update(prospect_id, status=outcome, next_followup_at=next_followup_at)
        self.store.event(prospect_id, "reply", outcome, {"next_followup_at": next_followup_at})
        return self.store.get(prospect_id)

    def campaign_summary(self, limit=20):
        prospects = self.store.list(limit=500)
        return {
            "total": len(prospects),
            "qualified": sum(1 for p in prospects if p["score"] >= 45 and not p["do_not_contact"]),
            "contacted": sum(1 for p in prospects if p["status"] == "contacted"),
            "suppressed": sum(1 for p in prospects if p["do_not_contact"]),
            "top": prospects[:max(1, min(int(limit), 50))],
            "policy": {
                "bulk_send": False,
                "manual_approval_per_send": True,
                "max_sends_per_day": self.max_sends_per_day,
                "max_sends_per_domain": self.max_sends_per_domain,
                "min_send_interval_seconds": self.min_send_interval,
            },
        }

    def _assert_contactable(self, p: dict, require_email: bool):
        if p.get("do_not_contact"):
            raise PermissionError("Ce prospect est dans la liste d'exclusion")
        email = p.get("public_email", "")
        domain = domain_from_email(email)
        if self.store.is_suppressed(email, domain):
            raise PermissionError("Ce contact ou ce domaine est supprimé")
        if require_email and not email:
            raise ValueError("Aucun e-mail professionnel public vérifié")

    def _assert_rate_limits(self, email: str):
        now = time.time()
        if self.store.sends_since(now - 86400) >= self.max_sends_per_day:
            raise PermissionError("Limite quotidienne de prospection atteinte")
        domain = domain_from_email(email)
        if domain and self.store.sends_since(now - 86400, domain) >= self.max_sends_per_domain:
            raise PermissionError("Limite quotidienne pour ce domaine atteinte")
        last = self.store.last_send_at()
        if last and now - float(last) < self.min_send_interval:
            raise PermissionError("Délai minimal entre deux envois non respecté")
