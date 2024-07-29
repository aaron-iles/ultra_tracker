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
   caltopo_credential_id: XXXXXXXXXXXX
   caltopo_key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
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
   - ```caltopo_credential_id```: This is the tricky one to obtain. See the instructions down below on managing Caltopo credentials.
   - ```caltopo_key```: This is the tricky one to obtain. See the instructions down below on managing Caltopo credentials.
   - ```tracker_marker_name```: This is the literal name of the marker that represents the runner on the map. This was created in step 2 above.
   - ```route_name```: The literal name of the line in Caltopo that represents the route.
   - ```aid_stations```: This is a list of dictionaries representing the aid stations on the map. For each aid station you must have the ```name``` and ```mile_mark```.
5. From the ```/proj/ultra_tracker``` directory, start the application!
  ```yaml
  docker compose up
  ```

### Caltopo Authentication Information
To use this application youst must be able to authenticate with Caltopo. All credit for this authentication method goes to https://sartopo-python.readthedocs.io/en/latest/credentials.html. To do this you need to determine these values:

- account ID (6 characters)
- credential ID (12 characters)
- public key (44 characters)

This section only refers to your CalTopo account credentials which are not the same as your external account provider credentials (Google, Yahoo, MSN, Apple, etc.). This module does not need credentials for your external account provider.

Your CalTopo account may have multiple sets of credentials. These show up in the "Credentials" section at the bottom of the "Your Account" dialog.

To open the "Your Account" dialog, sign in to caltopo.com then click your login ID name, to the right of "Your Data" near the top right of the web interface. Don’t worry if no credentials are listed yet.

Each credential has a "credential ID" (the 12-character code shown in the Credentials table), and a "public key", which takes a bit more work to find.

Currently, the public key is most easily determined during the process of creating a new credential.

To create a new credential and to determine its credential ID and public key, follow these steps (based on the README at https://github.com/elliottshane/sme-sartopo-mapsrv):

1. Open a web page to caltopo.com. Make sure you are signed in to your account: you should see your user name or login name at the top right, to the right of "Your Data".
2. In a separate browser tab, go to https://caltopo.com/app/activate/offline?redirect=localhost. This should show a web page similar to the one used during CalTopo Desktop activation from the CalTopo Desktop Installation instructions. Don’t click Sync Account yet.
3. Open the developer console of your browser and start monitoring network traffic. For Chrome, use F12 to open Chrome DevTools; network traffic logging should be on when you open DevTools, as indicated by a red square-in-circle near the top left, which would stop monitoring network traffic when clicked.
4. Type "ultra_tracker" or a similar name for "Your device will be synced as". The exact name is not important, but can help you keep track of credentials in case you have several. Afterwards, the name you enter here will show up in the Credentials section of the Your Account dialog as above.
5. Check the checkbox and click Sync Account. (This should load an error page, which is OK.)
6. In the network traffic monitor, you will see many requests. After a few seconds, you can stop or pause network traffic monitoring to make sure the important entry does not get scrolled away as more new traffic happens.
7. In the first few requests, at the top of the list, you should see a request similar to:
```text
finish-activate?code=........&name=......
```
8. Write down or copy the 8-character value after `code=` from that request. This is not the value to put in the configuration file; you will use it in the next step.
9. In a new browser tab, go to: `caltopo.com/api/v1/activate?code=<code>` replacing `<code>` with the 8-character code from the previous step.
10. This should load a page that looks like the following (possibly all compressed into one line):
```json
{
  "code": "XXXXXXXXXXX",
  "account": {
    "id": "ABC123",
    "type": "Feature",
    "properties": {
      "subscriptionExpires": 1554760038,
      "subscriptionType": "pro-1",
      "subscriptionRenew": true,
      "subscriptionStatus": "active",
      "title": "......@example",
      "class": "UserAccount",
      "updated": 1554760038,
      "email": "......@example.com"
    }
  },
  "key": "xXXXXxXXXXXXXXXxxxXXXXxXxXXXXXXXXXXXX="
}
```
11. Copy the 12-character "code" value as `caltopo_credential_id` in the `race_config.yml` file. Enter the 44-character value of "key" as `caltopo_key` in the configuration file.
