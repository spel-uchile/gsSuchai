#include <stdio.h>
#include <csp/csp.h>
#include <csp/interfaces/csp_if_kiss.h>

#include <csp/drivers/usart.h>
#include <csp/arch/csp_thread.h>

#define PORT 10
#define S_ADDRESS 10		//source
#define D_ADDRESS 10		//destiny
#define R_ADDRESS 9			//tnc node (router)

#define SERVER_TIDX 0
#define CLIENT_TIDX 1
#define USART_HANDLE 0

//toopazo's definitions and includes
#include "kiss.h"
#define PACKET_ASCII 1

#include <zmq.h>
#include "zhelpers.h"
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>


CSP_DEFINE_TASK(task_server) {

    int running = 1;
    csp_socket_t *socket = csp_socket(CSP_SO_NONE);
    csp_conn_t *conn;
    csp_packet_t *packet;
    csp_packet_t *response;

    response = csp_buffer_get(sizeof(csp_packet_t) + 2);
    if( response == NULL ) {
        fprintf(stderr, "Could not allocate memory for response packet!\n");
        return CSP_TASK_RETURN;
    }
    response->data[0] = 'O';
    response->data[1] = 'K';
    response->length = 2;

    csp_bind(socket, CSP_ANY);
    csp_listen(socket, 5);

    printf("Server task started\r\n");
	int i;
	int obufflen;


    while(running) {
        if( (conn = csp_accept(socket, 10000)) == NULL ) {
            continue;
        }
	    printf("llego un paquete, ping, etc.. \r\n");
        while( (packet = csp_read(conn, 100)) != NULL ) {
            switch( csp_conn_dport(conn) ) {
                case PORT:
                   //if( packet->data[0] == 'q' )
                        //running = 0;
					if(PACKET_ASCII==1){
					    printf("%s", packet->data );
					}
					else{
						obufflen = packet->length;
						for(i=0;i<obufflen;i++){
						    printf("0x%X", packet->data[i] );
						}
				    	printf("\n");
					}

                    csp_buffer_free(packet);
                    csp_send(conn, response, 1000);
                    break;
                default:
                    csp_service_handler(conn, packet);
                    break;
            }
        }

        csp_close(conn);
    }

    csp_buffer_free(response);

    return CSP_TASK_RETURN;
}

CSP_DEFINE_TASK(task_client) {

    char outbuf = 'q';
    char outbuf2 = 'a';
    char inbuf[3] = {0};
    int pingResult;

	int i;
	int obufflen = 255;
	char obuff[obufflen];
	for(i=0;i<obufflen;i++){
		obuff[i]=100+i;
	}
	int ibufflen = 255;
	char ibuff[ibufflen];
	for(i=0;i<ibufflen;i++){
		ibuff[i]='\0';
	}
    printf("sizeof(data) = %d\n", obufflen );


	/*
    for(int i = 50; i <= 200; i+= 50) {
        pingResult = csp_ping(D_ADDRESS, 1000, 100, CSP_O_NONE);
        printf("Ping with payload of %d bytes, took %d ms\n", i, pingResult);
        csp_sleep_ms(1000);
    }

    csp_ps(D_ADDRESS, 1000);
    csp_sleep_ms(1000);
    csp_memfree(D_ADDRESS, 1000);
    csp_sleep_ms(1000);
    csp_buf_free(D_ADDRESS, 1000);
    csp_sleep_ms(1000);
    csp_uptime(D_ADDRESS, 1000);
    csp_sleep_ms(1000);
	*/

    //csp_transaction(0, D_ADDRESS, PORT, 1000, &outbuf, 1, inbuf, 2);
    //printf("Quit response from server: %s\n", inbuf);

    printf("ready to receive packet->buffer\n");
	while(1){
		char *msi = mgetline();
		int lmsi = strlen(msi)+1;
	    printf("msi = %s\n", msi);
	    printf("lmsi =  %d\n", lmsi);
		/*
		FILE *fp = fopen("log.txt", "ab+");
		if(fp == NULL) //if file does not exist, create it
		{
			//do something about it
			return CSP_TASK_RETURN;
		}
		fprintf(fp, "Some text: %s\n", msi);
		fclose(fp);
		*/
    	csp_transaction(0, D_ADDRESS, PORT, 1000, msi, lmsi, ibuff, -1);
	    printf("Quit response from server: %s\n", ibuff);
		free(msi);
	}

	
    return CSP_TASK_RETURN;
}

CSP_DEFINE_TASK(task_tx) {
	printf("task_tx\n");

 	printf ("Connecting to hello world server…\n");
    void *context = zmq_ctx_new();
    void *requester = zmq_socket(context, ZMQ_REQ);
    zmq_connect(requester, "tcp://localhost:5555");

    int request_nbr;
    for (request_nbr = 0; request_nbr != 10; request_nbr++) {
        char buffer [10];
        printf("Sending Hello %d…\n", request_nbr);
        zmq_send(requester, "Hello", 5, 0);
        zmq_recv(requester, buffer, 10, 0);
        printf("Received World %d\n", request_nbr);
    }
    zmq_close(requester);
    zmq_ctx_destroy(context);
  
    return 0;
}
CSP_DEFINE_TASK(task_rx) {
	printf("task_rx\n");

 	//  Socket to talk to clients
    void *context = zmq_ctx_new();
    void *responder = zmq_socket(context, ZMQ_REP);
    int rc = zmq_bind(responder, "tcp://*:5555");
    assert(rc == 0);

    while (1) {
        char buffer [10];
        zmq_recv(responder, buffer, 10, 0);
        printf("Received Hello\n");
        sleep(1);          //  Do some 'work'
        zmq_send(responder, "World", 5, 0);
    }

    return 0;
}
CSP_DEFINE_TASK(task_pub) {
    //  Prepare our context and publisher
    void *context = zmq_ctx_new ();
    void *publisher = zmq_socket (context, ZMQ_PUB);
    int rc = zmq_bind (publisher, "tcp://*:5556");
    assert (rc == 0);
    rc = zmq_bind (publisher, "ipc://weather.ipc");
    assert (rc == 0);

    //  Initialize random number generator
    srandom ((unsigned) time (NULL));
    while (1) {
        //  Get values that will fool the boss
        int zipcode, temperature, relhumidity;
        zipcode     = randof (100000);
        temperature = randof (215) - 80;
        relhumidity = randof (50) + 10;

        //  Send message to all subscribers
        char update [20];
        sprintf (update, "%05d %d %d", zipcode, temperature, relhumidity);
        s_send (publisher, update);
    }
    zmq_close (publisher);
    zmq_ctx_destroy (context);
    return 0;
}
CSP_DEFINE_TASK(task_sub) {
    //  Socket to talk to server
    printf ("Collecting updates from weather server…\n");
    void *context = zmq_ctx_new ();
    void *subscriber = zmq_socket (context, ZMQ_SUB);
    int rc = zmq_connect (subscriber, "tcp://localhost:5556");
    assert (rc == 0);

    //  Subscribe to zipcode, default is NYC, 10001
    char *filter = "10001 ";
    rc = zmq_setsockopt (subscriber, ZMQ_SUBSCRIBE, filter, strlen (filter));
    assert (rc == 0);

    //  Process 100 updates
    int update_nbr;
    long total_temp = 0;
    for (update_nbr = 0; update_nbr < 100; update_nbr++) {
        char *string = s_recv (subscriber);

        int zipcode, temperature, relhumidity;
        sscanf (string, "%d %d %d",
            &zipcode, &temperature, &relhumidity);
        total_temp += temperature;
        free (string);
    }
    printf ("Average temperature for zipcode '%s' was %dF\n",
        filter, (int) (total_temp / update_nbr));

    zmq_close (subscriber);
    zmq_ctx_destroy (context);
    return 0;
}

int main(int argc, char **argv) {
  
	csp_debug_toggle_level(CSP_PACKET);
    csp_debug_toggle_level(CSP_INFO);

    csp_buffer_init(10, 300);
    csp_init(S_ADDRESS);

    struct usart_conf conf;

#if defined(CSP_WINDOWS)
    conf.device = argc != 2 ? "COM4" : argv[1];
    conf.baudrate = CBR_9600;
    conf.databits = 8;
    conf.paritysetting = NOPARITY;
    conf.stopbits = ONESTOPBIT;
    conf.checkparity = FALSE;
#elif defined(CSP_POSIX)
    conf.device = argc != 2 ? "/dev/ttyUSB0" : argv[1];
    conf.baudrate = 500000;
#elif defined(CSP_MACOSX)
    conf.device = argc != 2 ? "/dev/tty.usbserial-FTSM9EGE" : argv[1];
    conf.baudrate = 115200;
#endif

	usart_init(&conf);
	csp_kiss_init(usart_putstr, usart_insert);
	usart_set_callback(csp_kiss_rx);

    csp_route_set(R_ADDRESS, &csp_if_kiss, CSP_NODE_MAC);
    csp_route_start_task(0, 0);

    csp_conn_print_table();
    csp_route_print_table();
    csp_route_print_interfaces();

   
    csp_thread_handle_t handle_server;
    csp_thread_create(task_server, (signed char *) "SERVER", 1000, NULL, 0, &handle_server);
   	csp_sleep_ms(100);

    csp_thread_handle_t handle_client;
    csp_thread_create(task_client, (signed char *) "CLIENT", 1000, NULL, 0, &handle_client);

    csp_thread_handle_t handle_tx;
    csp_thread_create(task_tx, (signed char *) "TX", 1000, NULL, 0, &handle_tx);
	csp_sleep_ms(2000);
    csp_thread_handle_t handle_rx;
    csp_thread_create(task_rx, (signed char *) "RX", 1000, NULL, 0, &handle_rx);

	csp_sleep_ms(11000);
    csp_thread_handle_t handle_pub;
    csp_thread_create(task_pub, (signed char *) "PUB", 1000, NULL, 0, &handle_pub);
	csp_sleep_ms(2000);
    csp_thread_handle_t handle_sub;
    csp_thread_create(task_sub, (signed char *) "SUB", 1000, NULL, 0, &handle_sub);

    /* Wait for program to terminate (ctrl + c) */
    while(1) {
   		csp_sleep_ms(5000);
    }

    return 0;

}

char * mgetline(void) {
    char * line = malloc(100);
	char * linep = line;
    size_t lenmax = 100;
	size_t len = lenmax;
    int c;

    if(line == NULL)
        return NULL;

	for(;lenmax>0;lenmax--){
		line[lenmax-1]='\0';
	}


    for(;;) {
        c = fgetc(stdin);
        if(c == EOF)
            break;

        if(--len == 0) {
            len = lenmax;
            char * linen = realloc(linep, lenmax *= 2);

            if(linen == NULL) {
                free(linep);
                return NULL;
            }
            line = linen + (line - linep);
            linep = linen;
        }

        if((*line++ = c) == '\n')
            break;
    }
    *line = '\0';
    return linep;
}
