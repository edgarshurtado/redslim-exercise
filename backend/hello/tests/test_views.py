import pytest
from django.test import Client


@pytest.mark.django_db
def test_hello_endpoint_returns_200():
    client = Client()
    response = client.get('/redslim-hello')
    assert response.status_code == 200


@pytest.mark.django_db
def test_hello_endpoint_returns_message():
    client = Client()
    response = client.get('/redslim-hello')
    assert response.json() == {'message': 'Hello Redslim'}
