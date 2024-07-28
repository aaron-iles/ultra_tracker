#!/usr/bin/env python3




import sartopo


sts=sartopo.SartopoSession('caltopo.com','U5P1F',
      configpath='./sts.ini',
      account='ayi092@gmail.com')


sts.addFolder('testasdas')


#import requests
#import time
#import json
#import hmac
#import base64
#
#key = "gd3sTcBM/Afqk0ovCSUk80tv07NLUjrVZI2cjEizHEg="
#pre_url = "https://caltopo.com/api/v1/map/U5P1F"
#apiUrlEnd = "/Marker/e5780259-fb37-4b03-b311-1a1058cc8030"
#
#payload = {
#    "type": "Feature",
#    "id": "e5780259-fb37-4b03-b311-1a1058cc8030",
#    "properties": {
#        "title": "Aaron (estimated)",
#        "description": "None",
#        "folderId": "57847b8a-595e-47c9-81ac-22eaeb4b641d",
#        "marker-size": "1",
#        "marker-symbol": "a:4",
#        "marker-color": "FFFFFF",
#        "marker-rotation": 180,
#        "class": "Marker",
#    },
#}
#
#
#def _getToken(data: str) -> str:
#    """Internal method to get the token needed for signed requests.\n
#    Normally only called from _sendRequest.
#
#    :param data: Data to be signed
#    :type data: str
#    :return: Signed token
#    :rtype: str
#    """
#    # logging.info("pre-hashed data:"+data)
#    token = hmac.new(base64.b64decode(key), data.encode(), "sha256").digest()
#    token = base64.b64encode(token).decode()
#    # logging.info("hashed data:"+str(token))
#    return token
#
#
#expires = int(time.time() * 1000) + 120000  # 2 minutes from current time, in milliseconds
#data = f"POST {apiUrlEnd}\n{expires}\n{json.dumps(payload)}"
#params = {}
#params["id"] = "4NFH2U"
#params["expires"] = expires
#params["signature"] = _getToken(data)
#
#
#response = requests.post(
#    f"{pre_url}{apiUrlEnd}",
#    data=params,  # urlencode({"json": self.as_json}),
#    verify=True,
#    timeout=60,
#)
#
#print(response)
#import pdb; pdb.set_trace()
