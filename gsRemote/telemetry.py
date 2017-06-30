import pymongo
from bson.objectid import ObjectId
import json

from pymongo import MongoClient
    

class Telemetry():


    dictState = {
        0 : "Empty",
        1 : "In Progress",
        2 : "Finished",
        3 : "Broken",
        None : "Unkown"
    }

    dictPayload = {
        "tm_estado": 0,
        "battery": 1,
        "debug": 2,
        "lagmuirProbe": 3,
        "gps": 4,
        "camera": 5,
        "sensTemp": 6,
        "gyro": 7,
        "expFis": 8
    }

    # payloadList = [
    #     "tm_estado",
    #     "battery",
    #     "debug",
    #     "lagmuirProbe",
    #     "gps",
    #     "camera",
    #     "sensTemp",
    #     "gyro",
    #     "expFis"
    # ]

    payloadList = list(dictPayload.keys())
    
    def __init__(self):
        self.obj_id="None"
        self.date = None
        self.data = []
        self.n_data = 0
        self.last_frame = -1
        self.lost_p= 0
        self.l_data = 0
        self.payload = "None"
        self.p_status = "None"

        
        
        # state of the telemetry
        #    0 -> empty
        #    1 -> in progress
        #    2 -> finished
        #    3 -> broken
        self.state = 0
        
            
    def get_state(self):
        return self.state
    
    def set_state(self, st):
        self.state = st

    def set_date(self, date):
        self.date = date

    def set_obj_id(self, id):
        self.obj_id = id
    
    def get_data(self):
        return self.data

    def set_doc_data(self, dat):
        self.data = dat
        
    def set_data(self, dat, n_frame):
        self.data = self.data +  dat
        
        
        if int(n_frame, 16) != self.last_frame+1:
            #self.lost_p = self.lost_p  + (int(n_frame, 16) - self.last_frame+1) uncomment when bug has been fixed
            #print str(int(n_frame, 16)) + " " +  str(self.last_frame+1)
            self.lost_p = self.lost_p + 1 
            self.state = 3
            
        self.last_frame = int(n_frame, 16)
        self.n_data = self.n_data+1
        
    def get_n_data(self):
        return self.n_data
            
    def get_lost_p(self):
        return self.lost_p
    
    def get_l_data(self):
        return self.l_data


    def set_doc_l_data(self, data):
        self.l_data = data

    def set_l_data(self, l_data):
        self.l_data = int(l_data, 16)
        
    def get_payload(self):
        return self.payload

    def set_doc_payload(self, pay):
        self.payload = pay

    def set_payload(self, pay):
        self.payload = int(pay, 16)
        
    def get_p_status(self):
        return self.p_status

    def get_obj_id(self):
        return self.obj_id
    
    def set_p_status(self, p_status):
        self.p_status = p_status


    def set_last_frame(self, last_frame):
        self.last_frame = last_frame

    def get_last_frame(self):
        return self.last_frame

    def set_n_data(self, n_data):
        self.n_data = n_data

    def set_lost_p(self, lost_p):
        self.lost_p = lost_p

        
    def to_dict(self):
        return {
                "state"  : self.state,
                "payload": self.payload,
                "data" : self.data,
                "n_data" : self.n_data,
                "lost_p" : self.lost_p,
                "l_data" : self.l_data,
                "payload_status" : self.p_status
                }

    def save(self, client):
        if len(client.nodes) > 0:
            db = client.suchai1_tel_database
            if self.n_data > 0:
 #               dict = self.to_dict()
                dict = self.__dict__
                try:
                    self.insert_or_update(dict, self.get_collection(client))

                except pymongo.errors.DuplicateKeyError as e:
                    print("Duplicate Key: {0}".format(e))
                    print("data not saved")
                    return

            # print("saved telemetries")
        else:
            print("no connection")

    def get_collection(self, client):
        if len(client.nodes) > 0:
            db = client.suchai1_tel_database
            if self.n_data > 0:
                if self.payload == 0:
                    return db.tm_estado
                elif self.payload == 1:
                    return db.battery
                elif self.payload == 2:
                    return db.debug
                elif self.payload == 3:
                    return db.lagmuirProbe
                elif self.payload == 4:
                    return db.gps
                elif self.payload == 5:
                    return db.camera
                elif self.payload == 6:
                    return db.sensTemp
                elif self.payload == 7:
                    return db.gyro
                elif self.payload == 8:
                    return  db.expFis
                else:
                    return db.unknown

        return None

    @staticmethod
    def get_collection_with_payload( client, pay):
        if len(client.nodes) > 0:
            db = client.suchai1_tel_database
            if pay == 0:
                return db.tm_estado
            elif pay == 1:
                return db.battery
            elif pay == 2:
                return db.debug
            elif pay == 3:
                return db.lagmuirProbe
            elif pay == 4:
                return db.gps
            elif pay == 5:
                return db.camera
            elif pay == 6:
                return db.sensTemp
            elif pay == 7:
                return db.gyro
            elif pay == 8:
                return  db.expFis
            else:
                return db.unknown

        return None



    def insert_or_update(self, dict, collection):
        if self.obj_id != "None":
            res = collection.find_one(ObjectId(self.obj_id))
            if res != None:
                collection.update({'_id': ObjectId(self.obj_id)}, dict, True)
                print("updated object")

        else:
            res = collection.insert_one(dict)
            self.obj_id = res.inserted_id
            print("inserted object")