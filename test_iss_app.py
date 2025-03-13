import pytest
import requests
import numpy as np

  
# Integration tests for Flask routes
# Ensure the Flask server is already be running

def test_get_all_epochs():
    all_epochs_request = requests.get('http://127.0.0.1:5000/epochs')
    assert all_epochs_request.status_code == 200
    assert isinstance(all_epochs_request.text, str)

def test_get_some_epochs():
    some_epochs_request = requests.get('http://127.0.0.1:5000/epochs?limit=3&offset=472')
    assert some_epochs_request.status_code == 200
    assert isinstance(some_epochs_request.text, str)

def test_get_specific_epoch():
    specific_epoch_request = requests.get('http://127.0.0.1:5000/epochs/531')
    assert specific_epoch_request.status_code == 200
    assert isinstance(specific_epoch_request.text, str)
    
def test_get_speed():
    speed_request = requests.get('http://127.0.0.1:5000/epochs/296/speed')
    assert speed_request.status_code == 200
    assert isinstance(speed_request.text, str)

def test_get_location():
    location_request = requests.get('http://127.0.0.1:5000/epochs/582/speed')
    assert location_request.status_code == 200
    assert isinstance(location_request.text, str)
    
def test_get_now():
    now_request = requests.get('http://127.0.0.1:5000/now')
    assert now_request.status_code == 200
    assert isinstance(now_request.text, str)
    