import pymongo
import json

from pymongo import MongoClient
    

class Telemetry():
#    def enum(**enums):
#        return type('Enum', (), enums)
    
    def __init__(self):
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
    
    def get_data(self):
        return self.data
        
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
    
    def set_l_data(self, l_data):
        self.l_data = int(l_data, 16)
        
    def get_payload(self):
        return self.payload
    
    def set_payload(self, pay):
        self.payload = int(pay, 16)
        
    def get_p_status(self):
        return self.p_status
    
    def set_p_status(self, p_status):
        self.p_status = p_status
        
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
                
                if self.payload == 0:
                    db.tm_estado.insert_one(dict)
                elif self.payload == 1:
                    db.battery.insert_one(dict)
                elif self.payload == 2:
                    db.debug.insert_one(dict)
                elif self.payload == 3:
                    db.lagmuirProbe.insert_one(dict)
                elif self.payload == 4:
                    db.gps.insert_one(dict)
                elif self.payload == 5:
                    db.camera.insert_one(dict)
                elif self.payload == 6:
                    db.sensTemp.insert_one(dict)
                elif self.payload == 7:
                    db.gyro.insert_one(dict)
                elif self.payload == 7:
                    db.expFis.insert_one(dict)
                else:
                    db.unknown.insert_one(dict)
            print("saved telemetries")
        else:
            print("no connection")
                
        
        
        