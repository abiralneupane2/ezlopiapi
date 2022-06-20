
import json
import asyncio
from lib2to3.pgen2 import token

import mysql.connector

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import python_jwt as jwt, jwcrypto.jwk as jwk, datetime

PORT = 2000
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "ezlopi"
KEY = jwk.JWK.generate(kty='RSA', size=2048)


def register(data):
    c = db.cursor()
    dev_id = data["dev_id"]
    c.execute(f"INSERT INTO devices (dev_id) VALUES ({dev_id}) ON DUPLICATE KEY UPDATE dev_id={dev_id}")
    db.commit()
    return json.dumps({
        "id" : dev_id,
        "resp_id": data["cmd_id"]
    })

def provision_update(data):
    c = db.cursor()
    dev_id = data["dev_id"]
    c.execute(f"SELECT * FROM DEVICES WHERE dev_id = {dev_id}")
    
    provision_data = c.fetchall()
    if len(provision_data) != 1:
        raise Exception(f"provision data not found for device id {dev_id}")
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

class EzloSocket(WebSocket):

    def handleMessage(self):
        # echo message back to client
        try:
            data = json.loads(self.data)
            if data["cmd_id"] == 7:
                resp = register(data)
            elif data["cmd_id"] == 1:
                resp = provision_update(data)
            else:
                raise Exception("Invalid cmd_id")
            self.sendMessage(resp)
            
        except Exception as e:
            print(e)
            resp = json.dumps({
                "id" : data["dev_id"] or None,
                "resp_id": data["cmd_id"] or None,
                "error": -1,
                "err_msg": str(e)
            })
            self.sendMessage(resp)
        
        
        

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')




if __name__ == "__main__":
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("Db connected")
    except Exception as e:
        print(str(e))
    server = SimpleWebSocketServer('0.0.0.0', PORT, EzloSocket)
    server.serveforever()
    print(f"Server opened at port {PORT}")

