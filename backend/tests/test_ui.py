from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "BDNS Control Panel" in response.text


def test_dashboard_assets_are_served() -> None:
    with TestClient(app) as client:
        css_response = client.get("/ui/assets/styles.css")
        js_response = client.get("/ui/assets/app.js")
        assert css_response.status_code == 200
        assert js_response.status_code == 200
