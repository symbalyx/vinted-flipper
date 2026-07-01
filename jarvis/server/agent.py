"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5 — Boucle agentique + function-calling (le cerveau) ║
╚══════════════════════════════════════════════════════════════╝

Transforme JARVIS d'un système « 1 coup » (le LLM répond, on parse des tags) en
un véritable AGENT multi-tours : le modèle appelle un outil → voit le résultat →
continue → produit une réponse finale. Il peut donc enchaîner des actions,
réagir aux erreurs, et RÉSUMER les résultats (ex. recherche web).

Compatible DeepSeek (tools natifs) et Ollama récent (llama3.1/3.2, qwen2.5…).
Dégradation gracieuse : si le backend ne supporte pas tools=[], `run()` renvoie
None et l'appelant retombe sur l'ancien `execute_jarvis_commands`.
"""

import json
import logging

import requests

try:
    from execution_context import CURRENT_MISSION_ID, CURRENT_STEP_ID
except Exception:
    CURRENT_MISSION_ID = CURRENT_STEP_ID = None

logger = logging.getLogger("JARVIS.agent")


def _redact_tool_result(name, result):
    """Évite de recopier le contenu des e-mails, brouillons et workflows dans les logs."""
    text = str(result or "")
    private_results = {
        "email_previsualiser", "email_envoyer",
        "prospection_ajouter_prospect", "prospection_preparer_message",
        "prospection_envoyer_brouillon", "prospection_lister_prospects",
        "n8n_creer_workflow", "n8n_modifier_workflow",
        "lire_fichier", "presse_papier_lire",
    }
    if name in private_results:
        return f"<résultat masqué:{len(text)} caractères>"
    return text[:200]


def _redact_tool_args(name, args):
    """Réduit les données privées avant journalisation sans modifier l'appel réel."""
    if not isinstance(args, dict):
        return {}
    hidden = {"contenu", "texte", "corps", "workflow_json", "message"}
    out = {}
    for key, value in args.items():
        if key in hidden:
            text = str(value or "")
            out[key] = f"<masqué:{len(text)} caractères>"
        elif key in {"approval_token", "token", "api_key", "password"}:
            out[key] = "<secret>"
        else:
            out[key] = value
    return out


class ToolRegistry:
    """Chaque outil = un schéma JSON (pour le LLM) + un handler Python.

    Si un `permission_manager` est fourni, les outils SENSIBLES/CRITIQUES ne sont
    PAS exécutés directement : ils créent une demande d'approbation applicative
    (usage unique) que l'utilisateur confirme dans l'interface. Sans
    `permission_manager`, le comportement historique est conservé (tests inclus).
    """

    def __init__(self, permission_manager=None):
        self._tools = {}
        self.perms = permission_manager
        self.action_receipts = None

    def register(self, name, description, parameters, handler):
        required = [k for k, v in parameters.items() if not v.get("optional")]
        props = {k: {kk: vv for kk, vv in v.items() if kk != "optional"}
                 for k, v in parameters.items()}
        self._tools[name] = {
            "schema": {"type": "function", "function": {
                "name": name, "description": description,
                "parameters": {"type": "object", "properties": props, "required": required}}},
            "handler": handler,
        }

    def schemas(self):
        return [t["schema"] for t in self._tools.values()]

    def names(self):
        return list(self._tools)

    def call(self, name, args: dict, approval_token: str = None) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Outil inconnu : {name}"
        args = args or {}
        mission_id = CURRENT_MISSION_ID.get() if CURRENT_MISSION_ID is not None else ""
        step_id = CURRENT_STEP_ID.get() if CURRENT_STEP_ID is not None else ""
        # Lors de la confirmation HTTP, le ContextVar du sous-agent n'est plus
        # actif. Le jeton conserve donc le contexte exact de la demande.
        if approval_token and self.perms is not None and hasattr(self.perms, "peek"):
            appr = self.perms.peek(approval_token)
            if appr:
                mission_id = appr.get("context_id", "") or mission_id
                step_id = appr.get("step_id", "") or step_id

        # Si une action externe identique a déjà réussi pour cette étape, on
        # renvoie le reçu persistant au lieu de la rejouer après un crash.
        if self.action_receipts is not None and mission_id and step_id:
            receipt = self.action_receipts.get_action_receipt(
                mission_id, step_id, name, args)
            if receipt:
                if approval_token and self.perms is not None:
                    # Consomme le nouveau jeton exact, mais ne rejoue pas l'effet.
                    self.perms.confirm(approval_token, name, args)
                return ((receipt.get("result") or "Action déjà exécutée") +
                        "\n[idempotence: résultat réutilisé, action non rejouée]")

        # Contrôle des permissions : une action sensible/critique sans jeton crée
        # une demande d'approbation au lieu de s'exécuter (fail-closed).
        if self.perms is not None:
            allowed, info = self.perms.guard(name, args, approval_token)
            if not allowed:
                if info.get("approval") == "requise":
                    req = info["request"]
                    return (f"⏳ Action « {name} » ({info['level']}) en attente "
                            f"d'approbation (id={req['approval_id'][:8]}…). "
                            "Confirme-la dans l'interface pour l'exécuter.")
                return f"⛔ Action refusée : {info.get('message', 'non autorisée')}"
        try:
            value = tool["handler"](**args)
            result = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            if self.action_receipts is not None and mission_id and step_id:
                self.action_receipts.record_action_receipt(
                    mission_id, step_id, name, args, result)
            return result
        except Exception as e:
            logger.warning(f"Outil {name} a échoué: {e}")
            return f"Erreur outil {name}: {e}"   # le LLM voit l'erreur et peut réagir


def build_registry(powers, lights, apple_home, websearch, learning_engine,
                   apply_scene, security, emergency_dispatcher, memory=None, pc=None,
                   permission_manager=None, n8n_client=None, email_service=None,
                   prospecting_service=None):
    """Déclare les outils en les branchant sur le code EXISTANT (déjà durci)."""
    reg = ToolRegistry(permission_manager=permission_manager)
    S = lambda **k: dict(type="string", **k)
    B = lambda **k: dict(type="boolean", **k)
    I = lambda **k: dict(type="integer", **k)

    reg.register("controler_lumiere",
        "Allume/éteint, change la couleur ou la luminosité d'une lumière.",
        {"piece": S(description="salon, chambre, cuisine, bureau, entrée, ou 'toutes'"),
         "on": B(optional=True), "couleur": S(optional=True,
            description="rouge, vert, bleu, jaune, orange, rose, violet, cyan, blanc, chaud, froid"),
         "luminosite": I(optional=True, description="0-100")},
        lambda piece, on=None, couleur=None, luminosite=None: (
            learning_engine.record_room(piece) or
            lights.set_state(piece, on=on, color=couleur, bri=luminosite)))

    reg.register("activer_scene",
        "Active une scène prédéfinie.",
        {"nom": S(description="cinéma, soirée, réveil, bonne nuit, absence, retour")},
        lambda nom: apply_scene(nom))

    reg.register("recherche_web",
        "Cherche sur le web (actualité, fait récent, info inconnue). "
        "RÉSUME ensuite les résultats avec ta personnalité.",
        {"requete": S()},
        lambda requete: json.dumps(websearch.search(requete), ensure_ascii=False))

    reg.register("lire_page_web", "Lit/résume le contenu d'une page web (URL publique).",
        {"url": S()}, lambda url: websearch.read_page(url))

    reg.register("homepod_dire", "Fait parler JARVIS à voix haute sur une enceinte HomePod.",
        {"texte": S(), "enceinte": S(optional=True)},
        lambda texte, enceinte="": apple_home.say(texte, enceinte))

    reg.register("appletv", "Télécommande Apple TV (play, pause, menu, home, up, down, select…).",
        {"commande": S()}, lambda commande: apple_home.appletv_command(commande))

    reg.register("appletv_app", "Lance une app sur l'Apple TV (netflix, youtube, disney…).",
        {"nom": S()}, lambda nom: apple_home.appletv_launch(nom))

    reg.register("meteo", "Météo actuelle d'une ville.", {"ville": S()},
        lambda ville: powers.get_weather(ville))

    reg.register("info_systeme", "Infos système : CPU, RAM, disque, OS.", {},
        lambda: powers.pc_info())

    reg.register("heure", "Date et heure actuelles.", {},
        lambda: __import__("datetime").datetime.now().strftime("%A %d %B %Y, %H:%M:%S"))

    reg.register("lister_fichiers", "Liste les fichiers d'un dossier (zone autorisée).",
        {"chemin": S()}, lambda chemin: powers.list_files(chemin))
    reg.register("lire_fichier", "Lit un fichier texte (zone autorisée).",
        {"chemin": S()}, lambda chemin: powers.read_file(chemin))
    reg.register("ecrire_fichier", "Écrit dans un fichier (zone autorisée).",
        {"chemin": S(), "contenu": S()},
        lambda chemin, contenu: powers.write_file(chemin, contenu))

    reg.register("calculer", "Calcule une expression mathématique.",
        {"expression": S()}, lambda expression: powers.calculate(expression))
    reg.register("mot_de_passe", "Génère un mot de passe sécurisé.", {},
        lambda: powers.gen_password())
    reg.register("rappel", "Programme un rappel dans N minutes.",
        {"minutes": I(), "message": S()},
        lambda minutes, message: powers.set_reminder(int(minutes), message))

    def _remember(fait):
        if memory:
            memory.add(fait, kind="fact")
        return learning_engine.add_fact(fait)
    reg.register("memoriser",
        "Mémorise durablement un fait sur l'utilisateur (préférence, allergie, proche…).",
        {"fait": S()}, _remember)

    reg.register("armer_alarme", "Arme ou désarme l'alarme anti-intrusion.",
        {"armer": B()}, lambda armer: security.set_armed(bool(armer)))

    reg.register("appeler_hote", "Appelle l'hôte/propriétaire de la maison.",
        {"message": S(optional=True)}, lambda message="": emergency_dispatcher.call_owner(message))

    reg.register("processus_top", "Liste les processus qui consomment le plus.", {},
        lambda: powers.get_processes())
    reg.register("ouvrir_app", "Lance une application (chrome, firefox, vscode, spotify…).",
        {"nom": S()}, lambda nom: powers.open_app(nom))
    reg.register("ouvrir_url", "Ouvre une URL dans le navigateur.",
        {"url": S()}, lambda url: powers.open_url(url))

    # ── Contrôle PC (si dispo) ──
    if pc is not None:
        reg.register("capture_ecran", "Fait une capture d'écran du PC.", {},
            lambda: pc.screenshot()["msg"])
        reg.register("controle_media", "Contrôle le média du PC (play, pause, next, prev, mute, vol_up, vol_down).",
            {"action": S()}, lambda action: pc.media(action))
        reg.register("verrouiller_pc", "Verrouille la session du PC.", {}, lambda: pc.lock())
        reg.register("tuer_processus", "Termine un processus par nom ou PID.",
            {"cible": S()}, lambda cible: pc.kill_process(cible))
        reg.register("luminosite_ecran", "Règle la luminosité de l'écran (0-100).",
            {"niveau": I()}, lambda niveau: pc.brightness(int(niveau)))
        reg.register("presse_papier_lire", "Lit le contenu du presse-papier.", {},
            lambda: pc.clipboard_get())
        reg.register("presse_papier_ecrire", "Écrit dans le presse-papier.",
            {"texte": S()}, lambda texte: pc.clipboard_set(texte))
        reg.register("alimentation_pc",
            "Alimentation du PC : lock/sleep (ok), shutdown/restart/logoff (nécessitent confirmer=true).",
            {"action": S(), "confirmer": B(optional=True)},
            lambda action, confirmer=False: pc.power(action, confirm=bool(confirmer)))

    # ── n8n Public API : création en brouillon, activation séparée ──
    if n8n_client is not None:
        reg.register("n8n_statut", "Indique si le connecteur n8n est configuré.", {},
            lambda: n8n_client.status())
        reg.register("n8n_lister_workflows", "Liste les workflows n8n existants.",
            {"limite": I(optional=True)},
            lambda limite=50: n8n_client.list_workflows(limit=int(limite or 50)))
        reg.register("n8n_creer_workflow",
            "Crée un workflow n8n INACTIF depuis un JSON n8n valide. Les nœuds système risqués sont refusés par défaut.",
            {"workflow_json": S(description="JSON complet avec name, nodes et connections")},
            lambda workflow_json: n8n_client.create_workflow(workflow_json))
        reg.register("n8n_modifier_workflow",
            "Met à jour un workflow n8n existant sans l'activer.",
            {"workflow_id": S(), "workflow_json": S()},
            lambda workflow_id, workflow_json: n8n_client.update_workflow(workflow_id, workflow_json))
        reg.register("n8n_activer_workflow", "Active un workflow n8n après approbation humaine.",
            {"workflow_id": S()}, lambda workflow_id: n8n_client.activate_workflow(workflow_id))
        reg.register("n8n_desactiver_workflow", "Désactive un workflow n8n après approbation humaine.",
            {"workflow_id": S()}, lambda workflow_id: n8n_client.deactivate_workflow(workflow_id))

    # ── E-mail SMTP : prévisualisation libre, envoi toujours CRITICAL ──
    if email_service is not None:
        reg.register("email_previsualiser",
            "Valide et prévisualise un e-mail sans l'envoyer.",
            {"destinataire": S(), "objet": S(), "corps": S(), "cc": S(optional=True)},
            lambda destinataire, objet, corps, cc="": email_service.preview(destinataire, objet, corps, cc))
        reg.register("email_envoyer",
            "Envoie réellement un e-mail SMTP. Une approbation humaine est toujours obligatoire.",
            {"destinataire": S(), "objet": S(), "corps": S(), "cc": S(optional=True)},
            lambda destinataire, objet, corps, cc="": email_service.send(destinataire, objet, corps, cc))

    # ── CRM de prospection : sources publiques, déduplication, brouillons ──
    if prospecting_service is not None:
        reg.register("prospection_ajouter_prospect",
            "Ajoute un prospect professionnel depuis une source publique vérifiable. Aucune adresse privée ni donnée sensible.",
            {"company_name": S(), "source_url": S(), "website": S(optional=True),
             "public_email": S(optional=True), "contact_name": S(optional=True),
             "region": S(optional=True), "notes": S(optional=True),
             "consent_basis": S(optional=True)},
            lambda company_name, source_url, website="", public_email="", contact_name="",
                   region="", notes="", consent_basis="public_b2b":
                prospecting_service.add_prospect(
                    company_name, source_url, website, public_email, contact_name,
                    region=region, notes=notes, consent_basis=consent_basis))
        reg.register("prospection_lister_prospects",
            "Liste les prospects du CRM, classés par score et état.",
            {"limite": I(optional=True), "statut": S(optional=True),
             "score_min": I(optional=True)},
            lambda limite=50, statut="", score_min=0:
                prospecting_service.list_prospects(limite or 50, statut or "", score_min or 0))
        reg.register("prospection_qualifier",
            "Recalcule le score d'un prospect à partir des preuves enregistrées.",
            {"prospect_id": S()},
            lambda prospect_id: prospecting_service.qualify(prospect_id))
        reg.register("prospection_preparer_message",
            "Crée un brouillon honnête et personnalisé. N'envoie rien.",
            {"prospect_id": S(), "offre": S(optional=True),
             "nom_expediteur": S(optional=True), "demo_url": S(optional=True)},
            lambda prospect_id, offre="création ou amélioration de site web",
                   nom_expediteur="Symbalyx", demo_url="":
                prospecting_service.prepare_message(
                    prospect_id, offre, nom_expediteur, demo_url))
        reg.register("prospection_envoyer_brouillon",
            "Envoie un seul brouillon CRM après contrôle anti-spam et approbation humaine individuelle.",
            {"draft_id": S()},
            lambda draft_id: prospecting_service.send_draft(draft_id, email_service))
        reg.register("prospection_exclure",
            "Ajoute un prospect à la liste de non-contact et empêche tout nouvel envoi.",
            {"prospect_id": S(), "raison": S(optional=True)},
            lambda prospect_id, raison="opposition ou exclusion manuelle":
                prospecting_service.suppress(prospect_id, raison))
        reg.register("prospection_resume",
            "Donne les statistiques et les meilleurs prospects, sans envoyer de message.", {},
            lambda: prospecting_service.campaign_summary())

    return reg


class Agent:
    def __init__(self, ai_engine, registry, learning_engine=None,
                 event_log=None, memory=None, max_turns=5,
                 raise_on_turn_limit=False):
        self.ai = ai_engine
        self.reg = registry
        self.learn = learning_engine
        self.event_log = event_log
        self.memory = memory
        self.max_turns = max_turns
        self.raise_on_turn_limit = bool(raise_on_turn_limit)

    def run(self, user_msg: str, system_prompt: str, hist=None, on_save=None,
            on_progress=None):
        # hist : historique à utiliser (ex. une conversation précise). Par défaut
        # l'historique global de l'IA. on_save : callback de persistance.
        H = hist if hist is not None else self.ai.history
        save = on_save or self.ai._save_history
        # Mémoire RAG : injecte les souvenirs pertinents
        if self.memory:
            souvenirs = self.memory.recall(user_msg, k=4)
            if souvenirs:
                system_prompt += "\n\n[SOUVENIRS PERTINENTS] " + " | ".join(souvenirs)

        H.append({"role": "user", "content": user_msg})
        messages = [{"role": "system", "content": system_prompt}] + list(H)

        for _turn in range(self.max_turns):
            reply = self._call_llm(messages)
            if reply is None:
                H.pop()                             # annule l'ajout user (fallback prendra le relais)
                return None                         # backend sans tool-use → fallback
            msg = reply.get("message", {})
            messages.append(msg)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                final = msg.get("content", "") or "…"
                H.append({"role": "assistant", "content": final})
                save()
                return final
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}") if isinstance(
                        fn.get("arguments"), str) else (fn.get("arguments") or {})
                except Exception:
                    args = {}
                logged_args = _redact_tool_args(name, args)
                logger.info(f"🛠️  {name}({logged_args})")
                if self.learn:
                    self.learn.record_command(name)
                result = self.reg.call(name, args)
                if self.event_log:
                    self.event_log.add("outil", f"{name}({json.dumps(logged_args, ensure_ascii=False)})",
                                       meta={"result": _redact_tool_result(name, result)})
                messages.append({"role": "tool",
                                 "tool_call_id": tc.get("id", name),
                                 "name": name, "content": result[:4000]})
                if on_progress:
                    try:
                        on_progress({"turn": _turn + 1, "tool": name,
                                     "args": logged_args, "result": result[:2000]})
                    except Exception:
                        logger.debug("Checkpoint agent non enregistré", exc_info=True)
        # Limite de tours atteinte. Dans une mission durable, ce n'est jamais un
        # succès : l'orchestrateur doit retenter/replanifier au lieu de marquer
        # l'étape terminée sur une phrase incomplète.
        if self.raise_on_turn_limit:
            raise RuntimeError(
                f"Limite interne de {self.max_turns} tours atteinte avant résultat final")
        final = "J'ai atteint la limite de cette interaction sans résultat final vérifiable."
        H.append({"role": "assistant", "content": final})
        save()
        return final

    def _call_llm(self, messages):
        tools = self.reg.schemas()
        try:
            if self.ai.backend == "deepseek":
                r = requests.post(self.ai.base_url,
                    headers={"Authorization": f"Bearer {self.ai.api_key}",
                             "Content-Type": "application/json"},
                    json={"model": self.ai.model, "messages": messages,
                          "tools": tools, "tool_choice": "auto", "temperature": 0.7},
                    timeout=45)
                r.raise_for_status()
                return {"message": r.json()["choices"][0]["message"]}
            else:  # ollama
                r = requests.post(self.ai.base_url,
                    json={"model": self.ai.model, "messages": messages,
                          "tools": tools, "stream": False}, timeout=120)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.warning(f"Tool-use indisponible ({e}) → fallback parser de tags.")
            return None
