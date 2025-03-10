# Homework 05: The Fountains of Flask
## Description
The purpose of this project is to use a Flask app to retrieve a large dataset related to the ISS using requests, parse the data, perform some calculations, and output some key findings to the screen for the user to read. The dataset as a whole has data related to the ISS over a span of 15 days, including the timestamp, position, and velocity of the ISS. Furthermore, we combine our Flask app with Docker containerization, ensuring our software is portable.

## Program Requirements
### Getting the Input Data
There is no need for the user to download the data manually. Instead, the program will dynamically request the data at runtime from the following URL:  
https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml

### Dependencies
To simplify working with dependencies, I containerize my application. Furthermore, I use requirements.txt to simplify dependency management within my container. My program makes use of the following libraries that are not in the Python standard library. These are all included in requirements.txt, which is copied to the container, and the libraries are recursively installed:  
- flask
- requests
- xmltodict  
- pytest
- numpy

## Building the Docker Image
In this repository, I include the Dockerfile as well as all of the source code. First, in your terminal, navigate into the homework05 directory. Then, to build the image, run the following:  
```docker build -t <username>/hw5:1.0 .```   

Make sure you specify your Docker Hub username in *<username>*. This might take a few moments, as it retrieves both my image and the base image (python 3.12), as well as downloading all dependencies.  

Alternatively, you could also pull the image from Docker Hub with the following, since my image is public:  
```docker pull lukevenk1/hw5:1.0```

## Running the Application
Once you have built the Docker image, you can run either the main script or the unit tests.  

### Run the main script
Before running, you need to ensure port 5000 on your host machine is not already allocated. If there is another container running on that port, remove that container. You can remove all containers on your host machine with the following command:  
```docker rm -f `docker ps -aq` ```

To run the main script, type the following into the terminal:  
```docker run --name "iss_app" -d -p 5000:5000 <username>/hw5:1.0```  
We run the container in the background using the "-d" option, so you can proceed to access various URL routes while the Flask app runs. Furthermore, using the "-p" option, we map port 5000 on the Jetstream VM to port 5000 in the container.

### Accessing URL routes
To retrieve useful information from the Flask app, we use curl to access routes. Here are the commands you should use. Keep in mind that these requests might take a few seconds.  

To return a list of the epochs, run the following:  
```curl localhost:5000/epochs```  

By default, it will only print out 10 epochs, starting from the first epoch, in order to not clutter the screen. If you wish to specify the number of epochs to show and the starting index, use these query parameters:  
```curl "localhost:5000/epochs?limit=<int>&offset=<int>"```  
Be sure to put the URL route in quotation marks, and to enter integer values for the limit and offset query parameters.

To return the state vectors for a specific epoch index, run the following:  
```curl localhost:5000/epochs/<int>```

To return the instantaneous speed for a specific epoch in the dataset, run the following:  
```curl localhost:5000/epochs/<int>/speed```

Finally, to return the state vector and speed for the epoch in the dataset closest to the time of execution, run the following:  
```curl localhost:5000/now```

### Run the unit tests
If you wish to run the unit tests instead, first, ensure that you ran the main script with the command above. If the Flask app is not actively running, these tests cannot work. Then, type the following into the terminal:  
```docker exec -it iss_app pytest /app```  
This will execute pytest inside the container you built (named "iss_app"), on the app directory where the source code resides. Specifying the "-it" option makes the container interactive so you can see the formatted output. Running this command may take up to a minute, since each integration test makes its own request from the Flask app.

### Cleanup
When you are done using the app, take care to stop the container from running on your localhost:  
```docker stop iss_app ```

If you'd like, you can also remove the container with the following:  
```docker rm -f iss_app ```
