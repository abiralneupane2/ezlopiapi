# ezlopiapi
python 3.8

Db doesnt connect in container for now so:

edit .env file according to database


use following sql to create table devices

 CREATE TABLE `devices` (`dev_id` varchar(99) NOT NULL,`wifi_ssid` varchar(32) DEFAULT NULL, `wifi_password` varchar(63) DEFAULT NULL,  `token` varchar(255) DEFAULT NULL, `type` varchar(32) DEFAULT NULL, `name` varchar(64) DEFAULT NULL, PRIMARY KEY (`dev_id`)) 


$ pip install -r requirements.txt
$ python src/main.py
