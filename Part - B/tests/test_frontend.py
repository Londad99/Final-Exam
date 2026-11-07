from fastapi.testclient import TestClient

from nubara_agent import api


def test_frontend_assets_and_api_share_origin():
    with TestClient(api.app) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'lang="es"' in page.text
        for asset in ['/app.js', '/styles.css']:
            assert client.get(asset).status_code == 200
        assert client.get('/health').json()['status'] == 'ok'
        assert client.get('/docs').status_code == 200
        assert client.get('/.env').status_code == 404
        assert client.get('/runtime.sqlite3').status_code == 404
