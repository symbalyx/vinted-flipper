"""FaceBank : sanitisation des noms + anti-traversée de chemin."""
import tempfile
from pathlib import Path

from security_mod.detector import safe_person_id


def test_safe_person_id_rejects_traversal():
    assert safe_person_id("../../test") == "test"
    assert safe_person_id("../../../etc/passwd") == "etc_passwd"
    assert safe_person_id("/absolute/path") == "absolute_path"
    assert safe_person_id("..") == ""
    assert safe_person_id(".") == ""
    assert safe_person_id("") == ""
    assert safe_person_id("....//") == ""


def test_safe_person_id_normalizes_accents_and_specials():
    assert safe_person_id("Amélie Dupont") == "amelie_dupont"
    assert safe_person_id("a\\b/c") == "a_b_c"
    assert safe_person_id("nul\x00byte") == "nul_byte"


def test_enroll_rejects_traversal_name_without_creating_files():
    """8. Nom d'enrôlement '../../test' : rejeté, aucun fichier hors FaceBank."""
    import numpy as np
    from security_mod.detector import FaceBank

    with tempfile.TemporaryDirectory() as tmp:
        known = Path(tmp) / "known_faces"
        fb = FaceBank(known_dir=str(known))
        # Le nom traversant est NEUTRALISÉ ('../../test' -> 'test') : le dossier
        # cible reste confiné dans known_faces, jamais en dehors.
        fb.enroll("../../test", np.zeros((100, 100), dtype="uint8"))
        # Aucun fichier/dossier créé en dehors de known_faces (traversée bloquée).
        assert not (Path(tmp) / "test").exists()
        assert not (Path(tmp).parent / "test").exists()
        # Défense en profondeur : _person_dir refuse un chemin brut traversant.
        import pytest
        with pytest.raises(ValueError):
            fb._person_dir("../../test")


def test_person_dir_confined_to_known_dir():
    from security_mod.detector import FaceBank
    with tempfile.TemporaryDirectory() as tmp:
        fb = FaceBank(known_dir=str(Path(tmp) / "kf"))
        # safe_person_id neutralise déjà, mais _person_dir doit rester confiné.
        p = fb._person_dir("amelie")
        assert str(fb.known_dir) in str(p.resolve())
