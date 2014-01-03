
The Ground Station software is divided in two:
A Remote side and a Antenna Side

The Antenna Side Software drives the Radio (TNC-ICOM) to sending/receiving frames to/from the satellite
The Remote Side Software drives the Antenna Side Software sending and receving telecommands/telemetry  to/from the satellite.


Antenna Side Software (ASS):
licsp is the library from Gomspace (to interface with the NanoCom and TNC1), it is avaliable on github,
the version used here is checkout 10c3151ba619d9e0c8affe0b49abd854e4159074 

Modification to the libcsp
1) examples/kiss.c 
Starting point we took to develop the ASS. Running this modified examples create the threads to send/receive 
the frames and retransmit them to the RSS

2) wscript
We modify the lib to compile examples/kiss.c against, in order to add LIB=-lzmq  flag to the compiler

Remote Side Software (RSS):
Is conneted via ZMQ sockets with the Antenna Side Software as a Publisher-Subscriber topology


