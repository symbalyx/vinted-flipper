# Résultats de tests (réels)

Environnement : Python 3.11, `pip install flask flask-cors numpy psutil Pillow
opencv-python-headless pydantic pytest`.
> Note : en production, `requirements_v4.txt` installe `opencv-contrib-python`
> (avec `cv2.face`). Ici `opencv-python-headless` suffit : `HAS_FACE_RECOGNITION`
> est alors False et la reconnaissance faciale se dégrade gracieusement (tout
> visage = « inconnu »), sans casser les tests.

## `python -m compileall server tests`
```
$ python -m compileall -q server tests
compileall_exit=0
```
Aucune erreur de compilation.

## `pytest -q`
```
........................................................................ [ 57%]
.....................................................                    [100%]
142 passed in 1.91s
```
(48 historiques + 63 Gardien + 6 détecteur + 8 approbations/UI + 3 OS + 14 OSINT = **142**.)

## Détail par fichier (collecte)
```
tests/test_agent.py .................. 7   (historique)
tests/test_conversations.py .......... 4   (historique)
tests/test_endpoints.py ............... 11 (historique)
tests/test_security.py ............... 15  (historique)
tests/test_subsystems.py .............. 11 (historique)
tests/test_emergency_approval.py ...... 5  (nouveau)
tests/test_facebank_paths.py .......... 4  (nouveau)
tests/test_guardian_api.py ............ 12 (nouveau)
tests/test_guardian_policy.py ......... 14 (nouveau)
tests/test_guardian_security.py ....... 10 (nouveau)
tests/test_guardian_state_machine.py .. 9  (nouveau)
tests/test_tool_permissions.py ........ 9  (nouveau)
--------------------------------------------------
TOTAL : 111 (48 historiques + 63 nouveaux) — 100 % passent
```

## Couverture des scénarios obligatoires (Étape 17)
| # | Scénario | Test |
|---|---|---|
| 1 | Porche vide : aucune parole/strike/sirène | `test_guardian_state_machine::test_empty_porch_stays_idle` |
| 2 | Réponse modèle invalide ⇒ UNKNOWN, aucune action | `test_guardian_security::test_service_unknown_takes_no_action` |
| 3 | 5 images identiques ⇒ pas de sirène par le nombre | `test_guardian_state_machine::test_five_positive_frames_never_trigger_alert` |
| 4 | Personne connue ⇒ pas d'escalade auto | `test_guardian_state_machine::test_known_person_no_auto_escalation` |
| 5 | Inconnu sans geste ⇒ engagement poli, pas d'urgence | `..::test_unknown_person_polite_engage_no_emergency` |
| 6 | Contact porte répété ⇒ WARNING + notif, pas sirène | `..::test_repeated_door_contact_goes_warning_not_alert` |
| 7 | HTML malveillant du modèle ⇒ texte, jamais exécuté | `test_guardian_policy::test_html_payload_is_kept_as_plain_text...` + `test_guardian_security::test_html_payload_in_fields_is_data...` (+ `web/gardien.html` via `textContent`) |
| 8 | Enrôlement `../../test` ⇒ rejeté, aucun fichier hors FaceBank | `test_facebank_paths::test_enroll_rejects_traversal_name...` |
| 9 | JARVIS parle ⇒ pas retranscrit comme utilisateur | `web/gardien.html` (micro OFF par défaut, pas de boucle STT) ; audio temps réel non activé |
| 10 | LLM tente appel/kill/désarmer/écrire ⇒ approbation | `test_tool_permissions::test_sensitive_requires_approval_then_confirm` |
| 11 | Appel d'urgence sans confirmation ⇒ refusé | `test_emergency_approval::test_call_requires_confirmation` |
| 12 | Clé API absente des fichiers/logs navigateur | `test_guardian_api::test_gardien_page_has_no_apikey_and_no_external_script` |
| 13 | Tests historiques ⇒ tous passent | 48/48 verts |
