"""Planification de missions : JSON LLM strict avec repli déterministe."""
from __future__ import annotations

import json
import re
import uuid
from .models import MissionPlan, MissionStep

ROLES = {
    "analyst": "cadre le besoin, les contraintes, les risques et les critères de réussite",
    "researcher": "collecte les informations nécessaires et cite les éléments vérifiables",
    "automation_engineer": "conçoit ou modifie des automatisations et workflows n8n sûrs",
    "builder": "réalise les changements techniques demandés dans les limites autorisées",
    "communications": "prépare les communications externes sans les envoyer sans approbation",
    "security_auditor": "cherche les failles, abus possibles, secrets et permissions excessives",
    "verifier": "exécute les contrôles, tests et vérifie les livrables",
    "reporter": "synthétise les résultats, preuves, limites et prochaines actions",
    "prospecting_researcher": "identifie des entreprises pertinentes à partir de sources professionnelles publiques, sans collecter de données privées",
    "lead_qualifier": "évalue le besoin probable, la qualité des preuves, la pertinence commerciale et le risque de contact",
    "outreach_writer": "prépare des messages honnêtes, personnalisés et non trompeurs, sans envoi automatique",
    "compliance_reviewer": "vérifie provenance, minimisation des données, suppression, fréquence de contact et conformité anti-spam",
}


def _sid(seq: int) -> str:
    return f"s{seq}-{uuid.uuid4().hex[:8]}"


def fallback_plan(goal: str, max_steps: int = 12) -> MissionPlan:
    low = goal.lower()
    steps: list[MissionStep] = []

    def add(role, title, instructions, depends=None):
        seq = len(steps) + 1
        steps.append(MissionStep(_sid(seq), seq, role, title, instructions, depends or []))
        return steps[-1].id

    s1 = add("analyst", "Cadrer la mission",
             f"Analyse cette mission : {goal}. Définis le livrable, les limites, les critères de réussite et les actions qui nécessitent une approbation humaine.")
    parallel = []
    parallel.append(add("researcher", "Rassembler le contexte",
                        "Recherche les informations et dépendances indispensables. Ne collecte pas de données personnelles inutiles.", [s1]))
    if "n8n" in low or "workflow" in low or "automatis" in low:
        parallel.append(add("automation_engineer", "Concevoir le workflow n8n",
                            "Conçois un workflow n8n valide. Utilise les outils n8n disponibles ; crée-le en brouillon et n'active rien sans approbation.", [s1]))
    prospecting = any(k in low for k in ("prospect", "prospection", "client", "artisan", "lead", "commercial"))
    if prospecting:
        p1 = add("prospecting_researcher", "Rechercher des prospects publics pertinents",
                 "Recherche uniquement des entreprises ou professionnels via des sources publiques légitimes. Enregistre la source, évite les données privées et respecte les exclusions demandées.", [s1])
        p2 = add("lead_qualifier", "Qualifier et classer les prospects",
                 "Déduplique, vérifie les preuves, note l'adéquation, le besoin probable, la contactabilité et les risques. N'invente aucune information.", [p1])
        p3 = add("outreach_writer", "Préparer des brouillons personnalisés",
                 "Prépare des brouillons courts et honnêtes pour les meilleurs prospects. Ne prétends jamais avoir créé un site ou obtenu un résultat sans preuve. Aucun envoi automatique.", [p2])
        parallel.append(add("compliance_reviewer", "Contrôler la campagne de prospection",
                            "Vérifie les sources, la minimisation des données, la liste d'exclusion, la fréquence, le droit d'opposition et l'approbation individuelle avant tout envoi.", [p3]))
    elif any(k in low for k in ("mail", "email", "message", "contact")):
        parallel.append(add("communications", "Préparer la communication",
                            "Prépare le message externe. L'envoi réel doit passer par l'outil email et une approbation humaine explicite.", [s1]))
    if any(k in low for k in ("code", "application", "fichier", "site", "projet", "corrig", "cré")):
        parallel.append(add("builder", "Réaliser le travail",
                            "Effectue les changements demandés avec les outils disponibles, dans l'espace de travail autorisé. Ne contourne jamais une permission.", [s1]))
    if len(parallel) == 1:
        parallel.append(add("builder", "Exécuter la mission",
                            "Réalise le livrable demandé en utilisant seulement les outils autorisés et en produisant des preuves vérifiables.", [s1]))
    audit = add("security_auditor", "Audit indépendant",
                "Contrôle le résultat, les permissions, secrets, injections, effets externes et risques résiduels.", parallel)
    verify = add("verifier", "Valider le résultat",
                 "Exécute les tests ou contrôles pertinents. Ne déclare jamais un succès sans preuve.", parallel + [audit])
    add("reporter", "Rapport final",
        "Produit un rapport bref : travail effectué, fichiers/actions, preuves, approbations, limites et prochaine étape.", [verify])
    return MissionPlan("Plan de mission sécurisé avec validation indépendante", steps[:max_steps])


def _extract_json(text: str):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def plan_with_llm(goal: str, llm_callable=None, max_steps: int = 12) -> MissionPlan:
    if llm_callable is None:
        return fallback_plan(goal, max_steps)
    prompt = f"""Mission utilisateur : {goal}
Crée un plan exécutable par plusieurs sous-agents. Réponds UNIQUEMENT en JSON :
{{"summary":"...","steps":[{{"seq":1,"role":"analyst","title":"...","instructions":"...","depends_on":[]}}]}}
Rôles autorisés : {', '.join(ROLES)}.
Contraintes : 2 à {max_steps} étapes ; dépendances seulement vers des numéros antérieurs ; recherche/build peuvent être parallèles ; security_auditor puis verifier puis reporter à la fin ; pour la prospection, utilise prospecting_researcher, lead_qualifier, outreach_writer puis compliance_reviewer ; uniquement des sources professionnelles publiques, pas de données privées, pas de collecte derrière connexion, pas d'envoi de masse ; les mails, activations n8n, applications et actions externes exigent une approbation humaine ; aucun shell libre ni contournement de sécurité."""
    try:
        raw = llm_callable(prompt)
        data = _extract_json(raw)
        items = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(items, list) or not (2 <= len(items) <= max_steps):
            raise ValueError("nombre d'étapes invalide")
        id_by_seq = {}
        steps = []
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                raise ValueError("étape invalide")
            seq = int(item.get("seq", index))
            if seq != index:
                seq = index
            role = str(item.get("role", "builder"))
            if role not in ROLES:
                role = "builder"
            sid = _sid(seq)
            id_by_seq[seq] = sid
            deps = []
            for dep in item.get("depends_on", []):
                try: dep_i = int(dep)
                except Exception: continue
                if dep_i < seq and dep_i in id_by_seq:
                    deps.append(id_by_seq[dep_i])
            title = str(item.get("title") or f"Étape {seq}")[:160]
            instructions = str(item.get("instructions") or title)[:4000]
            steps.append(MissionStep(sid, seq, role, title, instructions, deps))
        return MissionPlan(str(data.get("summary") or "Plan généré")[:500], steps)
    except Exception:
        return fallback_plan(goal, max_steps)
