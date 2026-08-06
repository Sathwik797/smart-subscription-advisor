import os
import pytest
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_favicon_returns_200(client):
    response = client.get('/favicon.ico')
    assert response.status_code == 200
    assert 'image' in response.content_type

def test_nonexistent_route_returns_404_not_500(client):
    response = client.get('/nonexistent-route-for-testing-404')
    assert response.status_code == 404
