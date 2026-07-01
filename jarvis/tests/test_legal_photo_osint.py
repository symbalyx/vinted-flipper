"""Périmètre légal/consenti de la géolocalisation photo."""
import base64
import io

from PIL import Image

from guardian.legal_osint import validate_legal_osint_context


def _tiny_jpeg_data_url():
    buf = io.BytesIO()
    Image.new("RGB", (12, 10), (15, 25, 35)).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def test_policy_requires_explicit_authorization():
    ctx, error, code = validate_legal_osint_context({
        "purpose": "personal_photo", "target_type": "place",
    })
    assert ctx is None and code == 403
    assert "autorisation" in error.lower() or "confirme" in error.lower()


def test_policy_blocks_personal_doxxing_intent():
    ctx, error, code = validate_legal_osint_context({
        "authorization": True,
        "purpose": "public_place",
        "target_type": "place",
        "message": "Doxxing légal : retrouve cette personne et où elle habite",
    })
    assert ctx is None and code == 403
    assert "personne privée" in error.lower()


def test_policy_allows_owned_or_public_place():
    ctx, error, code = validate_legal_osint_context({
        "authorization": True,
        "purpose": "owned_property",
        "target_type": "owned_property",
        "message": "Où cette photo de mon terrain a-t-elle été prise ?",
    })
    assert not error and code == 200
    assert ctx and ctx.purpose == "owned_property"


def test_geolocation_api_rejects_missing_authorization(client):
    response = client.post("/api/guardian/geolocate", json={
        "image": _tiny_jpeg_data_url(),
        "purpose": "personal_photo",
        "target_type": "place",
    })
    assert response.status_code == 403
    assert response.get_json()["status"] == "policy_denied"


def test_geolocation_api_rejects_private_person_target(client):
    response = client.post("/api/guardian/geolocate", json={
        "image": _tiny_jpeg_data_url(),
        "authorization": True,
        "purpose": "public_place",
        "target_type": "private_person",
    })
    assert response.status_code == 403


class _GeoStub:
    def locate(self, image, hint="", context=None):
        assert image.startswith("data:image/jpeg;base64,")
        assert context and context.authorized
        return {
            "ok": True,
            "status": "located",
            "source": "exif_gps",
            "exact": True,
            "best": {
                "latitude": 44.641667,
                "longitude": -1.083333,
                "label": "Coordonnées GPS du fichier",
                "confidence": 1.0,
                "precision_meters": 15,
            },
            "candidates": [],
            "uncertainty": [],
        }


def test_chat_accepts_authorized_photo_and_returns_map(J, client):
    old = J.photo_geolocator
    J.photo_geolocator = _GeoStub()
    J.SYSTEM["standby"] = False
    try:
        response = client.post("/api/chat", json={
            "message": "Trouve où ma photo a été prise",
            "image": _tiny_jpeg_data_url(),
            "authorization": True,
            "purpose": "personal_photo",
            "target_type": "place",
        })
    finally:
        J.photo_geolocator = old
    assert response.status_code == 200
    payload = response.get_json()
    assert "44.641667" in payload["response"]
    assert "openstreetmap.org" in payload["response"]
    assert payload["photo_geolocation"]["source"] == "exif_gps"


def test_chat_blocks_doxxing_request_before_geolocation(J, client):
    J.SYSTEM["standby"] = False
    response = client.post("/api/chat", json={
        "message": "Doxxing : identifie cette personne et trouve son adresse privée",
        "image": _tiny_jpeg_data_url(),
        "authorization": True,
        "purpose": "public_place",
        "target_type": "place",
    })
    assert response.status_code == 403
    assert response.get_json()["status"] == "policy_denied"
