"""Photo → globe : EXIF, validation stricte, prudence des estimations et API."""
import base64
import io

from PIL import Image

from guardian.config import GuardianConfig
from guardian.geolocation import (
    PhotoGeolocator, gps_from_ifd, parse_visual_geolocation,
)


def _tiny_jpeg_data_url():
    buf = io.BytesIO()
    Image.new("RGB", (16, 12), (20, 30, 40)).save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def test_gps_ifd_converts_coordinates():
    gps = {
        1: "N", 2: ((44, 1), (38, 1), (30, 1)),
        3: "W", 4: ((1, 1), (5, 1), (0, 1)),
    }
    lat, lon = gps_from_ifd(gps)
    assert round(lat, 6) == 44.641667
    assert round(lon, 6) == -1.083333


def test_gps_ifd_accepts_byte_direction_references():
    gps = {
        1: b"S", 2: ((33, 1), (52, 1), (0, 1)),
        3: b"E", 4: ((151, 1), (12, 1), (0, 1)),
    }
    lat, lon = gps_from_ifd(gps)
    assert round(lat, 6) == -33.866667
    assert round(lon, 6) == 151.2


def test_visual_geo_invalid_json_is_unknown():
    candidates, doubts, err = parse_visual_geolocation("pas du json")
    assert candidates == [] and err


def test_visual_geo_candidate_is_never_gps_precise():
    raw = ('{"status":"estimated","candidates":[{"latitude":48.8584,'
           '"longitude":2.2945,"label":"Tour Eiffel","country":"France",'
           '"city":"Paris","confidence":0.91,"precision_meters":1,'
           '"evidence":["tour métallique"]}],"uncertainty":[]}')
    candidates, _, err = parse_visual_geolocation(raw)
    assert not err and candidates[0].precision_meters >= 100
    assert candidates[0].source == "vision_estimate"


class _Vision:
    name = "stub"
    def available(self):
        return True
    def analyze(self, image, prompt):
        return ('{"status":"estimated","candidates":[{"latitude":45.764,'
                '"longitude":4.8357,"label":"Lyon","country":"France",'
                '"city":"Lyon","confidence":0.8,"precision_meters":5000,'
                '"evidence":["architecture"]}],"uncertainty":["pas de panneau"]}')


def test_geolocator_marks_visual_result_not_exact():
    svc = PhotoGeolocator(GuardianConfig(), _Vision())
    out = svc.locate(_tiny_jpeg_data_url())
    assert out["ok"] and out["status"] == "estimated"
    assert out["exact"] is False and out["best"]["latitude"] == 45.764


def test_geolocator_rejects_non_image_base64():
    svc = PhotoGeolocator(GuardianConfig(), _Vision())
    out = svc.locate("data:image/jpeg;base64," + base64.b64encode(b"not an image").decode())
    assert not out["ok"] and out["status"] == "invalid_image"


def test_photo_geolocation_endpoint_requires_auth_and_image(J, client):
    unauth = J.app.test_client()
    assert unauth.post("/api/guardian/geolocate", json={"image": _tiny_jpeg_data_url()}).status_code == 401
    assert client.post("/api/guardian/geolocate", json={}).status_code == 400
