#!/usr/bin/env python

#import modules
try:
	#open serial port
	import serial
	#delays
	import time

except RuntimeError:
	print "Error importing modules"
	print "Try using 'sudo'"

#------------------------------------------------------------------------------
try:
	ser = serial.Serial( "/dev/ttyUSB0", 500000, timeout=5 )	# timeout = x[sec]
except serial.SerialException:
	print  "No connection on {0} could be established".format(self.__port)

#delay
time.sleep(1)

#read and show buff
nc =ser.inWaiting()
r=ser.read(nc)
print r

#clean input buffer
ser.flushInput()

#send ping
line = "ping 10 1 2\n"
ser.write(line)
ser.flush()

#delay
time.sleep(1)

#read and show buff
nc =ser.inWaiting()
r=ser.read(nc)

#print buffer
print "ascii:"
print r

#print KISS frame
print "kiss frame:"
a=0
rr=[]
for c in r:
	if(c=='\n'):
		a=1
	if(a==1 and c=='P'):
		break
	if(a==1):
		if(c!='\n'):
			rr.append(c)
			print hex(ord(c)) +", ",

#print rr

#close port
ser.close()
