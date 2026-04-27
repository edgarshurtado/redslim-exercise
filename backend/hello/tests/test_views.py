from rest_framework.test import APIClient


def test_hello_endpoint_returns_200():
    client = APIClient()
    response = client.get('/redslim-hello')
    assert response.status_code == 200


def test_hello_endpoint_returns_message():
    client = APIClient()
    response = client.get('/redslim-hello')
    assert response.json() == {'message': 'Hello Redslim'}
