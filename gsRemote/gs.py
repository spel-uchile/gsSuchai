#
#   Weather update client
#   Connects SUB socket to tcp://localhost:5556
#   Collects weather updates and finds avg temp in zipcode
#

import sys
import zmq
import time



context = zmq.Context()

# Socket to send messages on
sender = context.socket(zmq.PUSH)
sender.connect("tcp://192.168.11.69:5557")

while(True):
	sender.send("holaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
	print "sending packet\n",
	time.sleep(5)





#  Socket to talk to server
context = zmq.Context()
socket = context.socket(zmq.SUB)

print "Collecting updates from weather server..."
socket.connect("tcp://192.168.11.69:5556")

# Subscribe to zipcode, default is NYC, 10001
pub_filter = "TM:"
socket.setsockopt(zmq.SUBSCRIBE, pub_filter)

# Process updates
while(True):
	string = socket.recv()
	#_filter, temperature, relhumidity = string.split()
	#print "filter =" + str(_filter)
	#print "temperature =" + str(temperature)
	#print "relhumidity =" + str(relhumidity)
	#print "***********************"
	print string 
