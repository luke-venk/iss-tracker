#!/usr/local/bin/python3
from flask import Flask, request
import redis
import requests
import xmltodict
import numpy as np
import time
import logging
from astropy import coordinates, units
from astropy.time import Time
from geopy.geocoders import Nominatim


# CONFIGURATION
app = Flask(__name__)
rd = redis.Redis(host='redis-db', port=6379, db=0)
logging.basicConfig(level='DEBUG')
logging.debug('App created.')

# HELPER FUNCTIONS (not associated with a URL route)
def get_data() -> None:
    '''
    Loads data from local .data directory into the Redis database.
    If there is no data, retrieve data from the ISS website and
    load it into the database.
    
    Returns
        None: simply updates the Redis database with the data
            from online if necessary
    '''
    # If database is empty
    if len(rd.keys()) == 0:
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
        time_zone = all_data['ndm']['oem']['body']['segment']['metadata']['TIME_SYSTEM']
        ref_frame = all_data['ndm']['oem']['body']['segment']['metadata']['REF_FRAME']
        object_data = all_data['ndm']['oem']['body']['segment']['metadata']['OBJECT_NAME']
        state_vectors = all_data['ndm']['oem']['body']['segment']['data']['stateVector']
        
        # Store data in Redis database
        rd.set('time-zone', time_zone)
        rd.set('reference-frame', ref_frame)
        rd.set('object', object_data)
        rd.set('num-svs', len(state_vectors))
        # Use hash to store state vectors as dictionary-like objects
        for i in range(len(state_vectors)):
            sv = state_vectors[i]
            sv_data = {
                'epoch': sv['EPOCH'],
                'x-units': sv['X']['@units'], 'x-value': sv['X']['#text'],
                'y-units': sv['Y']['@units'], 'y-value': sv['Y']['#text'],
                'z-units': sv['Z']['@units'], 'z-value': sv['Z']['#text'],
                'x-dot-units': sv['X_DOT']['@units'], 'x-dot-value': sv['X_DOT']['#text'],
                'y-dot-units': sv['Y_DOT']['@units'], 'y-dot-value': sv['Y_DOT']['#text'],
                'z-dot-units': sv['Z_DOT']['@units'], 'z-dot-value': sv['Z_DOT']['#text'],
            }
            # Key will be "state-vector:" followed by its index
            rd.hset(f'state-vector:{i}', mapping=sv_data)
        logging.debug('Data has been written to Redis database')
    else:
        logging.debug('Data is already in database')

def calculate_speed(epoch: int) -> float:
    '''
    Given a epoch index, find three Cartesian velocity components
    Use these quantities to calculate the speed, which is equivalent
    to the magnitude of the three vector components.
    
    Arguments:
        epoch (int): the index of the epoch to evaluate
    Returns:
        speed (float): the speed of the object, in km/s
    '''
    sv_key = f'state-vector:{epoch}'
    x_dot = float(rd.hget(sv_key, 'x-dot-value'))
    y_dot = float(rd.hget(sv_key, 'y-dot-value'))
    z_dot = float(rd.hget(sv_key, 'z-dot-value'))
    logging.debug('All velocity components for speed were found.')
    speed = np.sqrt(x_dot ** 2 + y_dot ** 2 + z_dot ** 2)
    return speed

def get_time_closest_to_now() -> int:
    '''
    Find the index of the state vector in the database with 
    the time closest to the current time (i.e., the time at
    which the program is executed).
    
    Returns:
        current_index (int): index corrresponding to the state vector
            with the time closest to now
    '''
    closest_index = -1
    closest_time = float('inf')   # The closest time to now (seconds)
    # Get current UTC time as a Unix timestamp (seconds since Unix epoch)
    time_now = time.mktime(time.gmtime())  
    
    count = int(rd.get('num-svs'))
    for i in range(count):
        sv_time_stamp = rd.hget(f'state-vector:{i}', 'epoch').decode('utf-8')
        # Remove the unecessary .XXXZ from the timestamp
        clean_time_stamp = sv_time_stamp.split('.')[0]
        # Parse time-stamp into a readable format
        format_time_stamp = time.strptime(clean_time_stamp, '%Y-%jT%H:%M:%S')
        sv_time = time.mktime(format_time_stamp)
        if abs(sv_time - time_now) < closest_time:
            closest_time = abs(sv_time - time_now)
            closest_index = i
    return closest_index

def get_geodetic(epoch: int) -> tuple[float, float, float]:
    '''
    Given the index of the epoch to evaluate, find the
    geodetic coordinates of the ISS corresponding to
    that epoch.
    
    Argument:
        epoch (int): index of the epoch
    Returns:
        latitude (float): latitude of the ISS for that epoch
        longitude (float): longitude of the ISS for that epoch
        altitude (float): altitude of the ISS for that epoch
    '''
    sv_key = f'state-vector:{epoch}'
    
    # EME2000 coordinates
    x = float(rd.hget(sv_key, 'x-value'))
    y = float(rd.hget(sv_key, 'y-value'))
    z = float(rd.hget(sv_key, 'z-value'))
    
    # Handle time stamp of epoch
    strip_time_str = rd.hget(sv_key, 'epoch').decode('utf-8')
    time_stamp = time.strftime('%Y-%m-%d %H:%m:%S', time.strptime(strip_time_str[:-5], '%Y-%jT%H:%M:%S'))
    
    cartesian = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartesian, obstime=time_stamp)  # geocentric celestial reference system
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=time_stamp))  # international terrestrial reference system
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)
    
    return loc.lat.value, loc.lon.value, loc.height.value
    
def get_geoposition(epoch: int) -> float:
    '''
    Given the index of the epoch to evaluate, find the
    geoposition of the ISS corresponding to that epoch.
    
    Argument:
        epoch (int): index of the epoch
    Returns:
        geoposition (float): geoposition of the ISS for that epoch
    '''
    geocoder = Nominatim(user_agent='iss_tracker')
    # Use helper function to get geodetic coordinates
    lat, lon, _ = get_geodetic(epoch)
    geoloc = geocoder.reverse((lat, lon), zoom=15, language='en')
    return geoloc
    

# URL ROUTES
@app.route('/epochs', methods=['GET'])
def get_all_epochs() -> list[dict]:
    '''
    Uses the dataset to return a list of the epochs to the user.
    
    Optional Query Parameters:
        limit (int): maximum number of epochs to be returned
        offset (int): offset at which to begin returning epochs
    Returns:
        output_str: the string describing the of list of epochs, 
            adjusting for user-specified limit and offset as needed
    '''
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
    count = int(rd.get('num-svs'))
    if offset + limit >= count:
        logging.error('ERROR: Out of bounds')
        return 'You entered an offset and limit that goes out of bounds.\n'
    else:
        output_str = f'Here is a list of {limit} epochs, starting from data entry {offset + 1}.\n\n'
        for i in range(offset, offset + limit):
            output_str += f'Epoch #{i + 1}\n'
            output_str += get_specific_epoch(i) + '\n'
        return output_str

@app.route('/epochs/<int:epoch>', methods=['GET'])
def get_specific_epoch(epoch: int) -> str:
    '''
    Returns the state vector associated with a certain epoch.
    
    Arguments:
        epoch (int): index of the state vector to return
    Returns:
        output (str): all the information related to the state vector
    '''
    # Deal with date and time
    sv_key = f'state-vector:{epoch}'
    time_stamp = rd.hget(sv_key, 'epoch').decode('utf-8')
    clean_time_stamp = time_stamp.split('.')[0]
    format_ts = time.strptime(clean_time_stamp, '%Y-%jT%H:%M:%S')
    
    # Ensure each of hour, min, and second takes 2 integer digits, padding with 0 if needed
    sv_date = f'{format_ts.tm_mon:02d}-{format_ts.tm_mday:02d}-{format_ts.tm_year:04d}'.strip()
    sv_time = f'{format_ts.tm_hour:02d}:{format_ts.tm_min:02d}:{format_ts.tm_sec:02d}'
    
    # Handle state vector metrics
    x_units = rd.hget(sv_key, 'x-units').decode('utf-8')
    x_quantity = rd.hget(sv_key, 'x-value').decode('utf-8')
    y_units = rd.hget(sv_key, 'y-units').decode('utf-8')
    y_quantity = rd.hget(sv_key, 'y-value').decode('utf-8')
    z_units = rd.hget(sv_key, 'z-units').decode('utf-8')
    z_quantity = rd.hget(sv_key, 'z-value').decode('utf-8')
    xdot_units = rd.hget(sv_key, 'x-dot-units').decode('utf-8')
    xdot_quantity = rd.hget(sv_key, 'x-dot-value').decode('utf-8')
    ydot_units = rd.hget(sv_key, 'y-dot-units').decode('utf-8')
    ydot_quantity = rd.hget(sv_key, 'y-dot-value').decode('utf-8')
    zdot_units = rd.hget(sv_key, 'z-dot-units').decode('utf-8')
    zdot_quantity = rd.hget(sv_key, 'z-dot-value').decode('utf-8')
    
    object_data = rd.get('object').decode('utf-8')
    ref_frame = rd.get('reference-frame').decode('utf-8')
    
    logging.info('Successfully parsed the entire epoch data.')
    
    # Assemble output string
    output = ''
    output += f'The date is {sv_date}.\n'
    output += f'The time is {sv_time} ({rd.get('time-zone').decode('utf-8')}).\n'
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
    speed = calculate_speed(epoch)  # Use helper function to find speed
    speed_units = rd.hget(f'state-vector:{epoch}', 'x-dot-units').decode('utf-8')  # Units for speed
    
    output = f'The instantaneous speed of epoch {epoch} is {speed:.5f} {speed_units}.\n'
    return output

@app.route('/epochs/<int:epoch>/location')
def get_location(epoch: int) -> str:
    '''
    Given the index of the epoch to evaluate, find its
    geodetic coordinates and geoposition.
    
    Argument:
        epoch (int): index of the epoch
    Returns:
        output_str (str): An output string that returns
            the latitude, longitude, altitude, and geoposition
    '''
    lat, lon, alt = get_geodetic(epoch)
    geop = get_geoposition(epoch)
    
    lat_str = f'{lat:.3f}'
    lon_str = f'{lon:.3f}'
    alt_str = f'{alt:.3f}'
    obj_str = rd.get('object').decode('utf-8')
    units_str = rd.hget(f'state-vector:{epoch}', 'x-units').decode('utf-8')  # Units for position
    output_str = f'The geodetic coordinates of the {obj_str} are ({lat_str}, {lon_str}) at an altitude of {alt_str} {units_str}.\n'
    if geop:
        output_str += f'The geoposition of the {obj_str} is {geop}.\n'
    else: 
        output_str += f'The {obj_str} is not above an identifiable geoposition.\n'
    return output_str

@app.route('/now', methods=['GET'])
def get_now() -> str:
    '''
    Displays the state vector and instantaneous speed for 
    the epoch closest to the time of execution.
    
    Returns:
        output (str): The state vector and speed for now
    '''
    # TODO
    closest_time_index = get_time_closest_to_now()
    logging.debug(f'The index of the epoch with the closest time is {closest_time_index}.')
    sv_output = get_specific_epoch(closest_time_index)
    speed_output = get_speed(closest_time_index)
    output = f'Here is the information for the state vector closest to now.\n\n'
    output += f'{sv_output}\n\n'
    output += f'{speed_output}'
    return output
    

if __name__ == '__main__':
    get_data()
    app.run(debug=True, host='0.0.0.0')
    logging.debug('App running!')