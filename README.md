# Ultra Tracker

Ultra Tracker is a specialized tool designed for tracking a runner's progress through an ultramarathon. It is deployed in a containerized environment and powered by Flask and uWSGI. Additionally, it seamlessly integrates with CalTopo, providing comprehensive mapping capabilities to enhance the tracking experience.

## Features

- **Runner Tracking:** Monitor the real-time progress of runners throughout the ultramarathon.
- **Containerized Deployment:** Deploy Ultra Tracker easily in a containerized environment for scalability and portability.
- **Flask and uWSGI:** Utilize the Flask web framework and uWSGI application server for robust and efficient performance.
- **CalTopo Integration:** Integrate with CalTopo for advanced mapping and route visualization capabilities.

## Getting Started
### Non-software Requirements
1. A Garmin inReach device. In theory, this could also be done with Spot trackers, but the author has not tested this software with them.
2. A Garmin professional account. If the user already has a Garmin account it is easy to switch to a professional account. This is necessary to redirect the tracker's data to a personal server. The fee structure is a tad different.
3. A Caltopo account (a free account is sufficient). The author is working on removing this dependency.
4. A server with at least 4 GB of memory and 2 cores. This software has only been tested on servers running modern versions of GNU+Linux operating systems though it should work on any OS.
5. A publicly-facing URL that can direct traffic to and from your server.
### Software Requirements
- ```docker```
- ```docker-compose```
- ```git```

To get started with Ultra Tracker, follow these steps:

1. **Clone the Repository:** Clone the Ultra Tracker repository to your local machine using the following command:
   ```bash
   git clone https://github.com/aaron-iles/ultra_tracker.git
   ```
   Place your cloned repo in ```/proj/ultra_tracker``` on your hosting server.
2. **Set up a course in Caltopo:** Create a map in Caltopo and set the privacy to either `Public` or `URL` (recommened). Add the course route as a line and give it whatever name you wish. Add the aid stations as markers and name them how you would like. Lastly, add a marker for yourself that will act as the "tracker" and name it as you wish. (This will be changing in the future).
3. **Configure your Garmin inReach account:** This requires a professional account with Garmin as noted above. Log into Garmin Explore and navigate to the IPC section. This should be under Settings > Portal Connect. (https://explore.garmin.com/IPC).
   - Enable "Outbound Settings" and set the outbound URL to the publicly reachable URL of your server on which you will be running the tracker.
   - Set "Outbound Message Version" to "JSON_V3"
   - Set "Authentication Method" to "AuthorizationToken"
   - Generate a secure auth token and type it into the "Authorization Token" field.
4. **Create a race config:** Create a file at ```/proj/ultra_tracker/application/race_config.yml``` and populate it with the following:
   ```yaml
   race_name: My Race
   start_time: '2024-04-06T07:00:00'
   garmin_api_token: XXXXXXXX
   caltopo_map_id: XXXXX
   caltopo_session_id: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   tracker_marker_name: MyName
   route_name: Route
   aid_stations:
     - name: 01 Aid Station
       mile_mark: 7.6
     - name: 02 Aid Station
       mile_mark: 14.2
   ```
   - ```race_name```: This is the human-friendly name of the race/event. 
   - ```start_time```: This is the start time of the race. The format must be ```YYYY-mm-ddTHH:MM:SS```.
   - ```garmin_api_token```: This is the token you created in step 3 above.
   - ```caltopo_map_id```: The is the map ID of the map you created in step 2 above (see the URL of the map in your browser).
   - ```caltopo_session_id```: This is the tricky one to obtain. See the instructions down below on managing the session ID.
   - ```tracker_marker_name```: This is the literal name of the marker that represents the runner on the map. This was created in step 2 above.
   - ```route_name```: The literal name of the line in Caltopo that represents the route.
   - ```aid_stations```: This is a list of dictionaries representing the aid stations on the map. For each aid station you must have the ```name``` and ```mile_mark```.
5. From the ```/proj/ultra_tracker``` directory, start the application!
  ```yaml
  docker compose up
  ```

### Caltopo Session ID Information
Caltopo does not document its API though it is exposed. Managing session tokens and performing authentication is a little tricky. The author has found the following to be the easiest way to obtain your session ID:
1. Navigate to https://caltopo.com/
2. Log out
3. Open your browser's developer console and look at the network (or similar) tab where you can see network activity
4. Click "Log In" and check the box for "Remember Me" (this is critical!)
5. Log into your account as normal
6. When the log in is complete, look through the network activity for a GET request to https://caltopo.com/sideload/account/XXXXXX.json where `XXXXXX` is your Caltopo user ID (NOT your username).
7. Look at the request headers for something like this ```SESSION=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX```; this is your session ID and it should be good for 3 months as of this writing
