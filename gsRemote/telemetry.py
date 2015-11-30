import pymongo


class Telemetry():
#    def enum(**enums):
#        return type('Enum', (), enums)
    
    def __init__(self):
        self.date = None
        self.data = []
        self.n_data = 0;
        self.last_frame = -1
        self.lost_p= 0
        self.type = "None"
        
        # state of the telemetry
        #    0 -> empty
        #    1 -> in progress
        #    2 -> finished
        #    3 -> broken
        
        self.state = 0
#        client = MongoClient()
#        try:
#            self.db = client.telemetry_database    
#        except IOError as e:
#            self.db = client.test_database
            
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
            
    def get_type(self):
        return self.type
    
    def set_type(self, tp):
        self.type = tp
        
    def get_lost_p(self):
        return self.lost_p

        
 #   def save(self):
        
        