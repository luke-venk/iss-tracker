# ISS Tracker
## Description
The purpose of this project is to use a Flask app to output key information related to the ISS to the user. The dataset, originally from NASA, has data related to the ISS over a span of 15 days, including the timestamp, position, and velocity of the ISS; the data will be stored in a Redis NoSQL database in order to guarantee flexible and scalable storage. Finally, we combine our Flask app with Docker containerization, ensuring our software is portable.

## Program Requirements
### Getting the Input Data
There is no need for the user to download the data manually. Instead, the program will dynamically request the data at runtime from the following URL:  
https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml

### Dependencies
To simplify working with dependencies, I containerize my application. Furthermore, I use requirements.txt to simplify dependency management within my container. My program makes use of the following libraries that are not in the Python standard library. These are all included in requirements.txt, which is copied to the container, and the libraries are recursively installed:  
- flask
- redis
- requests
- xmltodict  
- astropy
- geopy
- numpy
- pytest

## Building the Docker Image
Before running, you need to ensure ports 5000 and 6379 on your host machine is not already allocated. If there is another container running on that port, remove that container. You can remove all containers on your host machine with the following command:  
```docker rm -f `docker ps -aq` ```

In this repository, I include the docker-compose.yml file and Dockerfile. First, in your terminal, navigate into the iss-tracker directory. Then, to build the image, run the following:  
```docker compose up --build```   

## Running the Application
Once you have built the Docker image, you can run the containers and either use the routes to query data, or run the unit tests. By default, Dockerfile specifies the default command to run the Flask app. Thus, there is no need to manually run the app.  

### Accessing URL routes
To retrieve useful information from the Flask app, we use curl to access routes. Here are the commands you should use. Keep in mind that these requests might take a few seconds. Be sure to only pass in positive integers as parameters.  

To return a list of the epochs, run the following:  
```curl localhost:5000/epochs```  

By default, it will only print out 10 epochs, starting from the first epoch, in order to not clutter the screen. If you wish to specify the number of epochs to show and the starting index, use these query parameters:  
```curl "localhost:5000/epochs?limit=<int>&offset=<int>"```  
Be sure to put the URL route in quotation marks, and to enter integer values for the limit and offset query parameters.

To return the state vectors for a specific epoch index, run the following:  
```curl localhost:5000/epochs/<int>```

To return the instantaneous speed for a specific epoch in the dataset, run the following:  
```curl localhost:5000/epochs/<int>/speed```

To return the geodetic coordinates and geolocation for a specific epoch in the dataset, run the following:  
```curl localhost:5000/epochs/<int>/location```

Finally, to return the state vector, speed, and location for the epoch in the dataset closest to the time of execution, run the following:  
```curl localhost:5000/now```

### Run the unit tests
If you wish to run the unit tests instead, first, ensure that you ran the main script with the command above. If the Flask app is not actively running, these tests cannot work. Then, type the following into the terminal:  
```docker ps -a```  
Find the container name that corresponds to the Flask app. Then type the following:  
```docker exec -it <container_id_name> pytest /app```  
This will execute pytest inside the container for the Flask app, on the app directory where the source code resides. Specifying the "-it" option makes the container interactive so you can see the formatted output. Running this command may take up to a minute, since each integration test makes its own request from the Flask app.

### Cleanup
When you are done using the app, take care to stop the Flask and Redis containers from running on your localhost:  
```docker compose down ```