#!/usr/local/bin/python3
from flask import Flask, request
import requests
import xmltodict
import time
import numpy as np
import logging


# CONFIGURATION
app = Flask(__name__)
logging.basicConfig(level='DEBUG')
logging.debug('App created.')

# HELPER FUNCTIONS (not associated with a URL route)

def get_data() -> dict:
    '''
    Using the URL to the NASA XML data, return a dictionary
    containing all the data for this application.
    
    Returns
        all_data (dict): The entire ISS dataset
    '''
    # Send a request to get the XML data from the NASA website
    url = 'https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml'
    headers = {'accept': 'application/xml;'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logging.error('ERROR: Request was unsuccessful!')
    else:
        logging.info('Request was successful.')

    # Parse necessary data
    all_data = xmltodict.parse(response.text)
    return all_data

def calculate_speed(state_vector: dict) -> float:
    '''
    Given a state vector, find three Cartesian velocity components
    Use these quantities to calculate the speed, which is equivalent
    to the magnitude of the three vector components.
    
    Arguments:
        state_vector (dict): the current state vector to evaluate
    Returns:
        speed (float): the speed of the object, in km/s
    '''
    x_dot = float(state_vector['X_DOT']['#text'])
    y_dot = float(state_vector['Y_DOT']['#text'])
    z_dot = float(state_vector['Z_DOT']['#text'])
    logging.debug('All velocity components for speed were found.')
    speed = np.sqrt(x_dot ** 2 + y_dot ** 2 + z_dot ** 2)
    return speed

def get_time_closest_to_now(state_vectors: list) -> int:
    '''
    Given the current time, and the list of state vectors, find the index
    of the state vector with the time closest to the current time (i.e.,
    the time at which the program is executed).
    
    Arguments:
        state_vectors (list): a list of all the state_vectors
    Returns:
        current_index (int): index corrresponding to the state vector
        with the time closest to now
    '''
    closest_index = -1
    closest_time = float('inf')   # The closest time to now (seconds)
    # Get current UTC time as a Unix timestamp (seconds since Unix epoch)
    time_now = time.mktime(time.gmtime())  
    for i in range(len(state_vectors)):
        sv_time_stamp = state_vectors[i]['EPOCH']
        # Remove the unecessary .XXXZ from the timestamp
        clean_time_stamp = sv_time_stamp.split('.')[0]
        # Parse time-stamp into a readable format
        format_time_stamp = time.strptime(clean_time_stamp, '%Y-%jT%H:%M:%S')
        sv_time = time.mktime(format_time_stamp)
        if abs(sv_time - time_now) < closest_time:
            closest_time = abs(sv_time - time_now)
            closest_index = i
    return closest_index

# URL ROUTES

@app.route('/epochs', methods=['GET'])
def get_all_epochs() -> list[dict]:
    '''
    Uses the dataset to return a list of the epochs to the user.
    
    Optional Query Parameters:
        limit (int): maximum number of epochs to be returned
        offset (int): offset at which to begin returning epochs
    Returns:
        state_vectors (list[dict]): the list of epochs, adjusting
            for user-specified limit and offset as needed
    '''
    all_data = get_data()
    state_vectors = all_data['ndm']['oem']['body']['segment']['data']['stateVector']
    
    # Handle query parameters
    try:
        limit = int(request.args.get('limit', 10))
    except ValueError as e:
        logging.error('ERROR: Limit parameter must be an integer.')
        return 'ERROR: Limit parameter must be an integer.\n'
    try:
        offset = int(request.args.get('offset', 0))
    except ValueError as e:
        logging.error('ERROR: Offset parameter must be an integer.')
        return 'ERROR: Offset parameter must be an integer.\n'

    # Use query parameters to return a subset of the data
    return state_vectors[offset: offset + limit]

@app.route('/epochs/<int:epoch>', methods=['GET'])
def get_specific_epoch(epoch: int) -> str:
    '''
    Returns the state vector associated with a certain epoch.
    
    Arguments:
        epoch (int): index of the state vector to return
    Returns:
        output (str): all the information related to the state vector
    '''
    # Parse the specific state vector to be printed
    all_data = get_data()
    state_vectors = all_data['ndm']['oem']['body']['segment']['data']['stateVector']
    state_vector = state_vectors[epoch]
    
    # Scrape miscellaenous data to be used for displaying information
    time_zone = all_data['ndm']['oem']['body']['segment']['metadata']['TIME_SYSTEM']
    ref_frame = all_data['ndm']['oem']['body']['segment']['metadata']['REF_FRAME']
    object_data = all_data['ndm']['oem']['body']['segment']['metadata']['OBJECT_NAME']
    
    # Deal with date and time
    time_stamp = state_vector['EPOCH']
    clean_time_stamp = time_stamp.split('.')[0]
    format_ts = time.strptime(clean_time_stamp, '%Y-%jT%H:%M:%S')
    
    # Ensure each of hour, min, and second takes 2 integer digits, padding with 0 if needed
    sv_date = f'{format_ts.tm_mon:02d}-{format_ts.tm_mday:02d}-{format_ts.tm_year:04d}'.strip()
    sv_time = f'{format_ts.tm_hour:02d}:{format_ts.tm_min:02d}:{format_ts.tm_sec:02d}'
    
    # Handle state vector metrics
    x_units, x_quantity = state_vector['X']['@units'], state_vector['X']['#text']
    y_units, y_quantity = state_vector['Y']['@units'], state_vector['Y']['#text']
    z_units, z_quantity = state_vector['Z']['@units'], state_vector['Z']['#text']
    xdot_units, xdot_quantity = state_vector['X_DOT']['@units'], state_vector['X_DOT']['#text']
    ydot_units, ydot_quantity = state_vector['Y_DOT']['@units'], state_vector['Y_DOT']['#text']
    zdot_units, zdot_quantity = state_vector['Z_DOT']['@units'], state_vector['Z_DOT']['#text']
    
    logging.info('Successfully parsed the entire epoch data.')
    
    # Assemble output string
    output = ''
    output += f'The date is {sv_date}.\n'
    output += f'The time is {sv_time} ({time_zone}).\n'
    output += f'The {object_data} position is (compared to frame {ref_frame}): \n'
    output += f'\tX: {x_quantity} {x_units}.\n'
    output += f'\tY: {y_quantity} {y_units}.\n'
    output += f'\tZ: {z_quantity} {z_units}.\n'
    output += f'The {object_data} velocity is: (compared to frame {ref_frame}) \n'
    output += f'\tX: {xdot_quantity} {xdot_units}.\n'
    output += f'\tY: {ydot_quantity} {ydot_units}.\n'
    output += f'\tZ: {zdot_quantity} {zdot_units}.\n'
    
    return output

@app.route('/epochs/<int:epoch>/speed', methods=['GET'])
def get_speed(epoch: int) -> str:
    '''
    Returns the speed of the ISS associated with a certain epoch.
    
    Arguments:
        epoch (int): index of the state vector speed to return
    Returns:
        output (str): the speed of the ISS
    '''
    # Get the specific state vector we want to print the speed of
    all_data = get_data()
    state_vectors = all_data['ndm']['oem']['body']['segment']['data']['stateVector']
    state_vector = state_vectors[epoch]
    
    speed = calculate_speed(state_vector)  # Use helper function to find speed
    speed_units = state_vector['X_DOT']['@units']  # Units for speed
    
    output = f'The instantaneous speed of epoch {epoch} is {speed:.5f} {speed_units}.\n'
    return output

@app.route('/now', methods=['GET'])
def get_now() -> str:
    '''
    Displays the state vector and instantaneous speed for 
    the epoch closest to the time of execution.
    
    Returns:
        output (str): The state vector and speed for now
    '''
    all_data = get_data()
    state_vectors = all_data['ndm']['oem']['body']['segment']['data']['stateVector']
    closest_time_index = get_time_closest_to_now(state_vectors)
    logging.debug(f'The index of the epoch with the closest time is {closest_time_index}.')
    sv_output = get_specific_epoch(closest_time_index)
    speed_output = get_speed(closest_time_index)
    output = f'Here is the information for the state vector closest to now.\n\n'
    output += f'{sv_output}\n\n'
    output += f'{speed_output}'
    return output
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    logging.debug('App running!')