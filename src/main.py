
import json
import asyncio
from threading import Thread
import copy
import time

import mysql.connector

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import python_jwt as jwt, jwcrypto.jwk as jwk, datetime
from envparse import env



PORT = 2000         #port for websocket server

KEY = jwk.JWK.generate(kty='RSA', size=2048)    #private key for token generation

env.read_envfile()

#db setup from env file

DB_HOST = env('MYSQL_HOST')
DB_USER = "root"
DB_PASSWORD = env('MYSQL_ROOT_PASSWORD')
DB_NAME = "ezlopi"


db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )


def register(data):             #register method for cmd_id 7
    print("registering")
    
    c = db.cursor()
    dev_id = data["dev_id"]
    c.execute(f"INSERT INTO devices (dev_id) VALUES ('{dev_id}') ON DUPLICATE KEY UPDATE dev_id='{dev_id}'")
    db.commit()
    return json.dumps({
        "id" : dev_id,
        "resp_id": data["cmd_id"]
    })

def provision_update(data):             #provisoin update method for cmd_id 1
    print("fetching data")
    c = db.cursor()
    dev_id = data["dev_id"]
    c.execute(f"SELECT * FROM DEVICES WHERE dev_id = '{dev_id}'")       #fetch data of dev_id
    
    provision_data = c.fetchall()
    if len(provision_data) != 1:                            #returns list but always one item must be there or raise exception
        raise Exception(f"provision data not found for device id '{dev_id}'")
    provision_data = provision_data[0]
    try:
        token = jwt.generate_jwt({"dev_id" : dev_id}, KEY, 'RS256')
    except:
        raise Exception("Token creation failed.")
    return json.dumps({
        "resp_id" : data["cmd_id"],
        "dev_id" : provision_data[0],
        "default_wifi_ssid" : provision_data[1] or 'nepaldigisys',
        "default_wifi_pass" : provision_data[2] or 'NDS_0ffice',
        "token" : token
    })

def handleMessageCoroutine(wsobj, data):            #coroutine for concurrent serving of devices
    print("data: ", wsobj.data, type(wsobj.data))
    try:
        print(data["cmd_id"])
        if data["cmd_id"] == 7:                     #register
            resp = register(data)
        elif data["cmd_id"] == 1:                   #provision update
            resp = provision_update(data)
        else:
            raise Exception("Invalid cmd_id")
        print("success")
        wsobj.sendMessage(resp)                     #return response
        
    except Exception as e:
        print("error", e)
        resp = json.dumps({
            "id" : data["dev_id"] or None,
            "resp_id": data["cmd_id"] or None,
            "error": -1,
            "err_msg": str(e)
        })
        wsobj.sendMessage(resp)                     #return error




class EzloSocket(WebSocket):

    def handleMessage(self):
        Thread(target=handleMessageCoroutine, args=(self, json.loads(self.data))).start()       #thread to handle message begins here
    
    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')






async def main():
    server = SimpleWebSocketServer('0.0.0.0', PORT, EzloSocket)
    await asyncio.create_task(server.serveforever())



if __name__ == "__main__":
    asyncio.run(main())

