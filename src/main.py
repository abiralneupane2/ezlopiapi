

import json
import asyncio
import time
import cgi
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs



import mysql.connector
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import python_jwt as jwt, jwcrypto.jwk as jwk, datetime
from envparse import env




PORT = 2001         #port for websocket server
HTTP_PORT = 2000    #port for http server
HTTP_HOSTNAME = 'localhost'

KEY = jwk.JWK.generate(kty='RSA', size=2048)    #private key for token generation

env.read_envfile()

#db setup from env file

DB_HOST = env('MYSQL_HOST')
DB_USER = "root"
DB_PASSWORD = env('MYSQL_ROOT_PASSWORD')
DB_NAME = "ezlopi"



connected_devices_ids = []
connected_devices_wsobjs = []




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



def handleMobileRequestCoroutine(httpobj, data):
    print("handle coroutine")
    print(data)
    try:
        dev_id = data["dev_id"]
        wifi_ssid = data["default_wifi_ssid"]
        wifi_password = data["default_wifi_pass"]
        
        c = db.cursor()
        sql = f"UPDATE devices SET wifi_ssid = '{wifi_ssid}', wifi_password = '{wifi_password}' WHERE dev_id = '{dev_id}'"
        c.execute(sql)
        db.commit()
        try:
            idx = connected_devices_ids.index(dev_id)
            connected_devices_wsobjs[idx].sendMessage(json.dumps(data))
        except Exception as e:
            print(str(e))
            # print(f"device of id {dev_id} is not currently online")
            
        httpobj.send_response(200)
    except Exception as e:
        print(str(e))
        httpobj.send_response(400)
    
    



class EzloSocket(WebSocket):

    def handleMessage(self):
        Thread(target=handleMessageCoroutine, args=(self, json.loads(self.data))).start()       #thread to handle message begins here
    
    def handleConnected(self):
        
        
        try:
            headers = str(self.request.headers)
            headers_list = headers.split('\n')
            for h in reversed(headers_list):
                temp = dev_id = h.split(':')
                if temp[0] == "dev_id":
                    dev_id = temp[1].lstrip()
                    connected_devices_ids.append(dev_id)
                    connected_devices_wsobjs.append(self)
                    break

            
            

        except Exception as e:
            print(str(e))
        
        
        print("connected: ", self.address)
        print("connected devices: ", connected_devices_ids)
        

    def handleClose(self):
        try:
            idx = connected_devices_wsobjs.index(self)
            del connected_devices_wsobjs[idx]
            del connected_devices_ids[idx]

        except Exception as e:
            print(e)
        print("Disconnected:", self.address)
        print("connected devices: ", connected_devices_ids)
        


class EzloHTTP(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        data = json.loads(post_body.decode('utf-8'))
        print("post data", data)
        handleMobileRequestCoroutine(self, data)
        




def main():
    server = SimpleWebSocketServer('0.0.0.0', PORT, EzloSocket)
    Thread(target=server.serveforever).start()
    print("WS server started at port %s" % (PORT))
    webServer = HTTPServer((HTTP_HOSTNAME, HTTP_PORT), EzloHTTP)
    Thread(target=webServer.serve_forever).start()
    print("HTTP server started http://%s:%s" % (HTTP_HOSTNAME, HTTP_PORT))



if __name__ == "__main__":
    main()

