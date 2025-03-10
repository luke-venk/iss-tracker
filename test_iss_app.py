import pytest
import requests
import numpy as np
from iss_app import calculate_speed
from iss_app import get_time_closest_to_now

  
# Normal unit tests for helper functions 
def test_closest_time():
    past_sv = {'EPOCH': '2000-001T12:00:00.000Z', 
                'X': {'@units': 'km', '#text': '0'},
                'Y': {'@units': 'km', '#text': '0'}, 
                'Z': {'@units': 'km', '#text': '0'},
                'X_DOT': {'@units': 'km/s', '#text': '0'}, 
                'Y_DOT': {'@units': 'km/s', '#text': '0'},
                'Z_DOT': {'@units': 'km/s', '#text': '0'}}
    present_sv = {'EPOCH': '2025-001T12:00:00.000Z', 
                'X': {'@units': 'km', '#text': '0'},
                'Y': {'@units': 'km', '#text': '0'}, 
                'Z': {'@units': 'km', '#text': '0'},
                'X_DOT': {'@units': 'km/s', '#text': '0'}, 
                'Y_DOT': {'@units': 'km/s', '#text': '0'},
                'Z_DOT': {'@units': 'km/s', '#text': '0'}}
    future_sv = {'EPOCH': '2050-001T12:00:00.000Z', 
                'X': {'@units': 'km', '#text': '0'},
                'Y': {'@units': 'km', '#text': '0'}, 
                'Z': {'@units': 'km', '#text': '0'},
                'X_DOT': {'@units': 'km/s', '#text': '0'}, 
                'Y_DOT': {'@units': 'km/s', '#text': '0'},
                'Z_DOT': {'@units': 'km/s', '#text': '0'}}
    assert get_time_closest_to_now([past_sv, present_sv, future_sv]) == 1
    
def test_calculate_speed():
    one_sv = {'X_DOT': {'@units': 'km/s', '#text': '1.0'}, 'Y_DOT': {'@units': 'km/s', '#text': '1.0'}, 'Z_DOT': {'@units': 'km/s', '#text': '1.0'}}
    zero_sv = {'X_DOT': {'@units': 'km/s', '#text': '0.0'}, 'Y_DOT': {'@units': 'km/s', '#text': '0.0'}, 'Z_DOT': {'@units': 'km/s', '#text': '0.0'}}
    one_one_sv = {'X_DOT': {'@units': 'km/s', '#text': '1.0'}, 'Y_DOT': {'@units': 'km/s', '#text': '0.0'}, 'Z_DOT': {'@units': 'km/s', '#text': '0.0'}}
    negative_sv = {'X_DOT': {'@units': 'km/s', '#text': '-1.0'}, 'Y_DOT': {'@units': 'km/s', '#text': '0.0'}, 'Z_DOT': {'@units': 'km/s', '#text': '-2.0'}}
    julia_sv = {'X_DOT': {'@units': 'km/s', '#text': '13.69'}, 'Y_DOT': {'@units': 'km/s', '#text': '42.42'}, 'Z_DOT': {'@units': 'km/s', '#text': '798.01'}}
    assert calculate_speed(one_sv) == pytest.approx(np.sqrt(3))
    assert calculate_speed(zero_sv) == pytest.approx(0.0)
    assert calculate_speed(one_one_sv) == pytest.approx(np.sqrt(1))
    assert calculate_speed(negative_sv) == pytest.approx(np.sqrt(5))
    assert calculate_speed(julia_sv) == pytest.approx(799.25392248)
    
# Integration tests for Flask routes
# For these integration tests to work, the Flask server must already be running

def test_get_all_epochs():
    all_epochs_request = requests.get('http://127.0.0.1:5000/epochs')
    assert all_epochs_request.status_code == 200
    assert isinstance(all_epochs_request.json(), list)

def test_get_specific_epoch():
    specific_epoch_request = requests.get('http://127.0.0.1:5000/epochs/66')
    assert specific_epoch_request.status_code == 200
    assert isinstance(specific_epoch_request.text, str)
    
def test_get_speed():
    speed_request = requests.get('http://127.0.0.1:5000/epochs/2/speed')
    assert speed_request.status_code == 200
    assert isinstance(speed_request.text, str)
    
def test_get_now():
    now_request = requests.get('http://127.0.0.1:5000/now')
    assert now_request.status_code == 200
    assert isinstance(now_request.text, str)
    