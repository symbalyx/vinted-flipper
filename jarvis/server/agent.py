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

logger = logging.getLogger("JARVIS.agent")


class ToolRegistry:
    """Chaque outil = un schéma JSON (pour le LLM) + un handler Python."""

    def __init__(self):
        self._tools = {}

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

    def call(self, name, args: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Outil inconnu : {name}"
        try:
            result = tool["handler"](**(args or {}))
            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Outil {name} a échoué: {e}")
            return f"Erreur outil {name}: {e}"   # le LLM voit l'erreur et peut réagir


def build_registry(powers, lights, apple_home, websearch, learning_engine,
                   apply_scene, security, emergency_dispatcher, memory=None, pc=None):
    """Déclare les outils en les branchant sur le code EXISTANT (déjà durci)."""
    reg = ToolRegistry()
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

    return reg


class Agent:
    def __init__(self, ai_engine, registry, learning_engine=None,
                 event_log=None, memory=None, max_turns=5):
        self.ai = ai_engine
        self.reg = registry
        self.learn = learning_engine
        self.event_log = event_log
        self.memory = memory
        self.max_turns = max_turns

    def run(self, user_msg: str, system_prompt: str, hist=None, on_save=None):
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
                logger.info(f"🛠️  {name}({args})")
                if self.learn:
                    self.learn.record_command(name)
                result = self.reg.call(name, args)
                if self.event_log:
                    self.event_log.add("outil", f"{name}({json.dumps(args, ensure_ascii=False)})",
                                       meta={"result": result[:200]})
                messages.append({"role": "tool",
                                 "tool_call_id": tc.get("id", name),
                                 "name": name, "content": result[:4000]})
        # Limite de tours atteinte
        final = "J'ai enchaîné plusieurs étapes mais je m'arrête là pour pas tourner en rond. 🌀"
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
