"""Organisation branding: public read, super-admin-only writes, colour/logo validation, palette generation."""

import io

from PIL import Image

from app.features.branding import palette, service
from tests.features.usage.test_token_quota import API, _world


def _image(fmt="PNG", size=(32, 32), color=(10, 20, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()


def test_palette_keeps_the_shipped_colours_and_generates_the_rest():
    brand = palette.css_scale("#3446b8")
    assert brand["500"] == "52 70 184" and brand["600"] == "34 48 158"  # the original palette, verbatim
    assert palette.css_scale("#e8c523")["900"] != "0 0 0"  # shades missing from the shipped palette are generated
    custom = palette.css_scale("#0f766e")
    assert custom["500"] == "15 118 110"
    assert [sum(map(int, custom[str(s)].split())) for s in (50, 300, 500, 700, 900)] == sorted((sum(map(int, custom[str(s)].split())) for s in (50, 300, 500, 700, 900)), reverse=True)  # light -> dark
    assert palette.button_contrast_ok("#0f766e") and not palette.button_contrast_ok("#f5f5a0") and palette.button_contrast_ok("#25b8b4")


async def test_branding_is_public_and_defaults_to_the_shipped_identity(client):
    r = await client.get(f"{API}/branding")  # no token: the login page needs it
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == service.DEFAULTS["name"] and body["colors"]["brand"] == "#3446b8" and body["logo_url"] is None
    assert set(body["palette"]) == {"brand", "accent", "teal", "ground"} and body["palette"]["ground"] == {"base": "20 43 64", "button": "22 59 72"}
    assert set(body["palette"]) == {"brand", "accent", "teal", "ground"} and body["palette"]["teal"]["500"] == "37 184 180"
    assert (await client.get(f"{API}/branding/logo")).status_code == 404


async def test_only_super_admin_edits_and_input_is_validated(client):
    superadmin, _, admin, _, user, *_ = await _world(client)
    for headers in (admin, user):
        assert (await client.put(f"{API}/admin/branding", json={"name": "X"}, headers=headers)).status_code == 403
        assert (await client.post(f"{API}/admin/branding/logo", files={"file": ("a.png", _image(), "image/png")}, headers=headers)).status_code == 403
    assert (await client.put(f"{API}/admin/branding", json={"name": "X"})).status_code in (401, 403)

    r = await client.put(f"{API}/admin/branding", json={"name": "  شرکت   نمونه  ", "short_name": "نمونه", "color_brand": "#0F766E", "tagline": None}, headers=superadmin)
    assert r.status_code == 200
    body = (await client.get(f"{API}/branding")).json()
    assert body["name"] == "شرکت نمونه" and body["short_name"] == "نمونه"  # whitespace collapsed
    assert body["colors"]["brand"] == "#0f766e" and body["palette"]["brand"]["500"] == "15 118 110"
    assert body["palette"]["ground"]["base"] == body["palette"]["brand"]["900"] and body["palette"]["ground"]["button"] == body["palette"]["brand"]["800"]
    assert body["tagline"] == service.DEFAULTS["tagline"]  # untouched

    for bad in ({"name": "   "}, {"name": "x" * 121}, {"color_brand": "blue"}, {"color_accent": "#12345"}, {"color_brand": "#f5f5a0"}, {"color_highlight": "#ffffe0"}):
        assert (await client.put(f"{API}/admin/branding", json=bad, headers=superadmin)).status_code == 400, bad
    assert (await client.put(f"{API}/admin/branding", json={"color_accent": "#ffe066"}, headers=superadmin)).status_code == 200  # accent never carries white text


async def test_logo_upload_serving_validation_and_removal(client):
    superadmin, *_ = await _world(client)
    url = f"{API}/admin/branding/logo"
    up = await client.post(url, files={"file": ("l.png", _image("PNG"), "image/png")}, headers=superadmin)
    assert up.status_code == 200 and up.json()["logo_url"].endswith("/branding/logo?v=1")
    served = await client.get(f"{API}/branding/logo")  # public
    assert served.status_code == 200 and served.headers["content-type"] == "image/png" and served.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in served.headers["cache-control"] and Image.open(io.BytesIO(served.content)).size == (32, 32)

    jpg = await client.post(url, files={"file": ("l.jpg", _image("JPEG"), "image/jpeg")}, headers=superadmin)
    assert jpg.json()["logo_url"].endswith("v=2") and (await client.get(f"{API}/branding/logo")).headers["content-type"] == "image/jpeg"

    bad = {
        "svg": b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "text": b"hello", "empty": b"",
        "gif": _image("GIF"), "huge_dimension": _image("PNG", (2100, 10)), "too_big": b"\x89PNG\r\n\x1a\n" + b"0" * (512 * 1024),
        "lying_type": b"%PDF-1.4 fake",
    }
    for name, data in bad.items():
        r = await client.post(url, files={"file": (f"{name}.png", data, "image/png")}, headers=superadmin)  # the claimed type is ignored
        assert r.status_code == 400, name
    assert (await client.get(f"{API}/branding")).json()["logo_url"].endswith("v=2")  # failed uploads changed nothing

    assert (await client.delete(url, headers=superadmin)).json()["logo_url"] is None
    assert (await client.get(f"{API}/branding/logo")).status_code == 404
    assert (await client.delete(url, headers=superadmin)).status_code == 404
