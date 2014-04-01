#include <stdio.h>
#include <csp/csp.h>
#include <csp/interfaces/csp_if_kiss.h>

#include <csp/drivers/usart.h>
#include <csp/arch/csp_thread.h>

#define PORT 10			//TM-TC port
#define DPORT 11		//Debug port
#define S_ADDRESS 10		//source
#define D_ADDRESS 0		//pic node
#define R_ADDRESS_TNC 9		//tnc node (router)
#define R_ADDRESS_TRX 5		//trx node (router)

#define SERVER_TIDX 0
#define CLIENT_TIDX 1
#define USART_HANDLE 0

//toopazo's definitions and includes
#include <jansson.h>
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

    //libcsp init
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

    //ZMQ init
    //  Prepare our context and publisher
    void *context = zmq_ctx_new ();
    void *publisher = zmq_socket (context, ZMQ_PUB);
    int rc = zmq_bind (publisher, "tcp://*:5556");
    assert (rc == 0);
    
    char update [200];
    char bf[200];

    // listen incomming packets
    while(running) {
        if( (conn = csp_accept(socket, 10000)) == NULL ) {
            continue;
        }
        
        while( (packet = csp_read(conn, 100)) != NULL ) {
            switch( csp_conn_dport(conn) ) {
                
                case PORT:
                    printf("task_server: Received CSP packet in address %d (len = %d)\n", D_ADDRESS, packet->length);

                    obufflen = packet->length;
                    if(PACKET_ASCII==1){				
                        for(i=0;i<obufflen;i++){
                            printf("%c", packet->data[i] );
                        }
                        printf("\n");
                    }
                    else{
                        for(i=0;i<obufflen;i++){
                            printf("0x%X", packet->data[i] );
                        }
                        printf("\n");
                    }
                
                    //send to gsRemote
                    printf("task_server: Resending as ZMQ packet\n");

                    for(i=0;i<(packet->length);i++){
                        bf[i] = packet->data[i];
                    }
                    bf[i]='\0';

                    // Send message to all "TM:" subscribers
                    sprintf (update, "TM: %s", bf);
                    s_send (publisher, update);

                    // libcsp tasks
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

    zmq_close (publisher);
    zmq_ctx_destroy (context);

    return CSP_TASK_RETURN;
}

CSP_DEFINE_TASK(task_client) {

    //libcsp
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

    //ZMQ
    //  Socket to receive messages on
    void *context = zmq_ctx_new ();
    void *receiver = zmq_socket (context, ZMQ_PULL);
    zmq_bind (receiver, "tcp://*:5557");

    //  Process tasks forever
    int st;
    while (1) {

        obufflen = 255;
        st = zmq_recv (receiver, obuff, obufflen, 0);
        if(st < obufflen){
            obufflen = st;	//number of receiver bytes (truncated if st>obufflen)
        }

        printf("task_client: Received ZMQ packet (len = %d)\n", obufflen);
        printf("task_client: Resending as CSP packet to address %d\n", D_ADDRESS);

        obuff[obufflen]='\0';
        decode_json(obuff);

        int nd;
        if(obuff[0]=='p'){
            if(obuff[1]=='s'){
                nd = D_ADDRESS;
            }
            if(obuff[1]=='t'){
                nd = R_ADDRESS_TRX;
            }

            for(int i = 0; i <= 5; i++) {
                pingResult = csp_ping(nd, 5000, 50, CSP_O_NONE);
                printf("Ping with payload of 50 bytes, took %d ms\n", pingResult);
                csp_sleep_ms(1000);
            }

        }

        csp_transaction(0, D_ADDRESS, DPORT, 1000, obuff, obufflen, ibuff, 0);
    }
    zmq_close (receiver);
    zmq_ctx_destroy (context);

    return CSP_TASK_RETURN;
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

    csp_route_set(R_ADDRESS_TNC, &csp_if_kiss, CSP_NODE_MAC);
    csp_route_set(D_ADDRESS, &csp_if_kiss, CSP_NODE_MAC);
    csp_route_set(R_ADDRESS_TRX, &csp_if_kiss, CSP_NODE_MAC);

    csp_route_start_task(0, 0);

    csp_conn_print_table();
    csp_route_print_table();
    csp_route_print_interfaces();


    csp_thread_handle_t handle_server;
    csp_thread_create(task_server, (signed char *) "SERVER", 1000, NULL, 0, &handle_server);
    csp_sleep_ms(100);

    csp_thread_handle_t handle_client;
    csp_thread_create(task_client, (signed char *) "CLIENT", 1000, NULL, 0, &handle_client);

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

void decode_json(char *str){

    //char str[]= "[{\"sha\": \"<the commit ID>\",\"commit\": {\"message\": \"<the commit message>\"}}]";
    //char str[]= "[[], {\"a\":1, \"b\":2},\"hola\", 13, true, false]";
    printf("json array: %s\n", str);

    json_t *root;
    json_error_t error;

    root = json_loads(str, 0, &error);

    if(!json_is_array(root))
    {
        fprintf(stderr, "error: root is not an array\n");
        json_decref(root);
        return 1;
    }
    printf("size = %d\n", json_array_size(root) );

    int i; json_t *data;
    for(i = 0; i < json_array_size(root); i++)
    {
        //json_is_object(const json_t *json) 
        //json_is_array(const json_t *json) 
        //json_is_string(const json_t *json) 
        //json_is_integer(const json_t *json)
        //json_is_real(const json_t *json)
        //json_is_true(const json_t *json)
        //json_is_false(const json_t *json)
        //json_is_null(const json_t *json)
    
        data = json_array_get(root, i);
        switch( json_typeof(data) ){
            case JSON_OBJECT:
                fprintf(stdout, "%d-th data type is JSON_OBJECT \n", i);
            break;
            case JSON_ARRAY:
                fprintf(stdout, "%d-th data type is JSON_ARRAY \n", i);
            break;
            case JSON_STRING:
                fprintf(stdout, "%d-th data type type is JSON_STRING\n", i);
                fprintf(stdout, "%d-th data value is \"%s\"\n", i, json_string_value(data) );   
            break;
            case JSON_INTEGER:
                fprintf(stdout, "%d-th data type is JSON_INTEGER \n", i);
                fprintf(stdout, "%d-th data value is %d\n", i, (int)json_integer_value(data) ); 
            break;
            case JSON_REAL:
                fprintf(stdout, "%d-th data type is JSON_REAL \n", i);
                fprintf(stdout, "%d-th data value is %f\n", i, json_real_value(data) ); 
            break;
            case JSON_TRUE:
                fprintf(stdout, "%d-th data type is JSON_TRUE \n", i);
            break;
            case JSON_FALSE:
                fprintf(stdout, "%d-th data type is JSON_FALSE \n", i);
            break;
            case JSON_NULL:
                fprintf(stdout, "%d-th data type is JSON_NULL \n", i);
            break;
        }
    }
    json_decref(root);
}

