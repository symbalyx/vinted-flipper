"""Règles de minimisation et d'anti-spam pour la prospection.

Ce module ne remplace pas un avis juridique. Il impose des garde-fous produit :
sources professionnelles publiques, finalité B2B, données minimales, exclusion et
absence d'envoi de masse automatique.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_BASES = {"public_b2b", "existing_relationship", "explicit_consent", "referral"}
GENERIC_LOCAL_PARTS = {
    "contact", "bonjour", "hello", "info", "commercial", "sales", "accueil",
    "office", "devis", "direction", "communication", "studio", "atelier",
}


def normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if not email:
        return ""
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("Adresse e-mail invalide")
    return email


def normalize_url(value: str, *, required: bool = False) -> str:
    url = str(value or "").strip()
    if not url:
        if required:
            raise ValueError("Une URL de source publique est requise")
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL publique invalide")
    if parsed.username or parsed.password:
        raise ValueError("Les URL avec identifiants sont refusées")
    return url[:2000]


def domain_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def domain_from_email(email: str) -> str:
    return email.rsplit("@", 1)[1].lower() if "@" in email else ""


def validate_basis(value: str) -> str:
    basis = str(value or "public_b2b").strip().lower()
    if basis not in ALLOWED_BASES:
        raise ValueError("Base de contact non autorisée")
    return basis


def validate_public_business_contact(email: str, website: str, source_url: str,
                                     basis: str) -> list[str]:
    """Retourne des avertissements ; lève une erreur pour les cas interdits."""
    basis = validate_basis(basis)
    source_url = normalize_url(source_url, required=True)
    website = normalize_url(website) if website else ""
    email = normalize_email(email) if email else ""
    warnings: list[str] = []
    if not email:
        warnings.append("Aucun e-mail public : préparer un contact manuel, ne pas deviner")
        return warnings
    local = email.split("@", 1)[0]
    email_domain = domain_from_email(email)
    site_domain = domain_from_url(website or source_url)
    if basis == "public_b2b":
        if not site_domain:
            raise ValueError("Domaine professionnel impossible à vérifier")
        same_org = email_domain == site_domain or email_domain.endswith("." + site_domain)
        generic = local in GENERIC_LOCAL_PARTS
        if not same_org and not generic:
            warnings.append(
                "L'e-mail ne correspond pas clairement au domaine officiel ; vérification humaine requise")
    return warnings


def safe_text(value: str, limit: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:limit]
