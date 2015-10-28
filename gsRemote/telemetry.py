import pymongo


class Telemetry():
#    def enum(**enums):
#        return type('Enum', (), enums)
    
    def __init__(self):
        self.date = None
        self.data = []
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
        
    def set_data(self, dat):
        self.data = self.data +  dat
            
    def get_type(self):
        return self.type
    
    def set_type(self, tp):
        self.type = tp

        
 #   def save(self):
        
        