#include <stdio.h>
#include <csp/csp.h>
#include <csp/interfaces/csp_if_kiss.h>
#include <csp/csp_endian.h>
    
#include <csp/drivers/usart.h>
#include <csp/arch/csp_thread.h>

#include <jansson.h>
#include <zmq.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>

#include "zhelpers.h"
#include "kiss.h"

#define PORT 10			//TM-TC port
#define DPORT 11		//Debug port
#define CPORT 12                //Commands port

#define S_ADDRESS 10		//source
#define D_ADDRESS 0		//pic node
#define R_ADDRESS_TNC  9	//tnc node (router)
#define R_ADDRESS_TRX  5	//trx node (router)
#define R_ADDRESS_OBC  0	//tnc node (router)
#define R_ADDRESS_GND 10	//trx node (router)

#define SERVER_TIDX 0
#define CLIENT_TIDX 1
#define USART_HANDLE 0

#define PACKET_ASCII 1

const char *type_tm = "tm";      //Message is telemetry
const char *type_cmd = "cmd";    //Message is console command
const char *type_tc = "tc";      //Message is telecomand
const char *type_db = "debug";   //Message is debug telecomand
const char *type_tnc = "tnc";    //Message is a tnc command
const char *type_trx = "trx";    //Message is a trx command

const char *dest_obc = "obc";    //Message is telecomand
const char *dest_trx = "trx";    //Message is debug telecomand
const char *dest_tnc = "tnc";    //Message is a tnc command
const char *dest_gnd = "gnd";    //Message is a trx command

nanocom_conf_t tnc_config;

int csp_timeout = 1000;          //CSP timeout en ms

/**
 * Server task
 * Reads messages from TNC using libcsp and delivers to remote clients using zmq
 */
CSP_DEFINE_TASK(task_server)
{

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

    //ZMQ init
    void *context = zmq_ctx_new();
    void *publisher = zmq_socket(context, ZMQ_PUB);
    int rc = zmq_bind(publisher, "tcp://*:5556");
    assert(rc == 0);
    
    int i;
    char buffer[1024];
    memset(buffer, '\0', 1024);

    // listen incomming packets
    while(running) {
        if( (conn = csp_accept(socket, 10000)) == NULL ) 
        {
            continue;
        }
        
        while( (packet = csp_read(conn, 100)) != NULL ) 
        {
            switch( csp_conn_dport(conn) )
            {
                
                case PORT:
                    printf("task_server: Received CSP packet in address %d (len = %d)\n", D_ADDRESS, packet->length);
                    
                    char tmp[10];
                    for(i=0; i<packet->length/2; i++)
                    {
                        sprintf(tmp, "0x%04X,", packet->data16[i]);
                        strcat(buffer, tmp);
                    }
                    
                    json_t *j_msg = json_pack("{s:s, s:s}",
                                            "type", "tm",
                                            "data", buffer);
                    
                    char *s_msg = json_dumps(j_msg, 0);
                
                    // Send message to all "TM:" subscribers
                    printf("task_server: Resending as ZMQ packet\n");
                    s_send (publisher, s_msg);

                    // libcsp tasks
                    csp_buffer_free(packet);
//                     csp_send(conn, response, 1000);
                    
                    free(j_msg);
                    free(s_msg);
                    memset(buffer, '\0', 1024);
                    
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


/**
 * Task clients
 * Read messages from remote clients using zmq and delivers to TNC using libcsp
 */
CSP_DEFINE_TASK(task_client)
{

    //ZMQ
    //Socket to receive messages on
    void *context = zmq_ctx_new();
    void *receiver = zmq_socket(context, ZMQ_PULL);
    zmq_bind(receiver, "tcp://*:5557");
    
    int i;
    char *message;
    json_t *root;
    json_t *data;
    json_t *type;
    json_error_t error;
    
    //Get config from TNC
    int con_resp = com_get_conf(&tnc_config, NODE_TNC, csp_timeout);
    if(!con_resp)
    {
        printf("Unable to get TNC configuration\n");
    }
    else
    {
        printf("--- TNC Configuration ---\n");
        com_print_conf(&tnc_config);
    }

    //Process tasks forever
    while(1)
    {
        message = s_recv(receiver);   
        if(!message) continue;
        
        printf("[Client] Received message: %s\n", message);
        
        root = json_loads(message, 0, &error);
        if(!root) continue;
        
        //Check message type and perform corresponding action
        type = json_object_get(root, "type"); 
        if(!type)
        {
            printf("[Client] Malformed message\n");
        }
        //TC message
        else if(strcmp(json_string_value(type), type_tc) == 0)
        {
            data = json_object_get(root, "data");
            int len = json_array_size(data);
            uint16_t buffer[len];
            json_t *num;
            
            for(i = 0; i < json_array_size(data); i++)
            {
                num = json_array_get(data, i);
                buffer[i] = (uint16_t)json_integer_value(num);
            }
            
            //TODO: Check this
            csp_transaction(0, D_ADDRESS, PORT, csp_timeout, buffer, len*sizeof(uint16_t), NULL, 0);
        }
        //Console command message
        else if(strcmp(json_string_value(type), type_cmd) == 0)
        {
            data = json_object_get(root, "data");
            char *data_buff = json_string_value(data);
            int len = strlen(data_buff);
            
            csp_transaction(0, D_ADDRESS, CPORT, csp_timeout, data_buff, len, NULL, 0);
        }
        //Debug message
        else if(strcmp(json_string_value(type), type_db) == 0)
        {
            data = json_object_get(root, "data");
            char *data_buff = json_string_value(data);
            int len = strlen(data_buff);
            
            csp_transaction(0, D_ADDRESS, DPORT, csp_timeout, data_buff, len, NULL, 0);
        }
        //TNC commands
        else if(strcmp(json_string_value(type), type_tnc) == 0)
        {
            data = json_object_get(root, "data");
            
            char *key;
            json_t *value;
            uint16_t ivalue;
            
            json_object_foreach(data, key, value) 
            {              
                //Set tx baud
                if(strcmp(key, "set_tx_baud") == 0)
                {
                    ivalue = (uint8_t)json_integer_value(value);
                    tnc_config.tx_baud = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Set rx baud
                else if(strcmp(key, "set_rx_baud") == 0)
                {
                    ivalue = (uint8_t)json_integer_value(value);
                    tnc_config.rx_baud = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Set do rs
                else if(strcmp(key, "set_do_rs") == 0)
                {
                    ivalue = (uint8_t)json_integer_value(value);
                    tnc_config.do_rs = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Set do random
                else if(strcmp(key, "set_do_random") == 0)
                {
                    ivalue = (uint8_t)json_integer_value(value);
                    tnc_config.do_random = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Set do viterbi
                else if(strcmp(key, "set_do_viterbi") == 0)
                {
                    ivalue = (uint8_t)json_integer_value(value);
                    tnc_config.do_viterbi = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Set preamble_length
                else if(strcmp(key, "set_preamble") == 0)
                {
                    ivalue = (uint16_t)json_integer_value(value);
                    tnc_config.preamble_length = ivalue;
                    com_set_conf(&tnc_config, NODE_TNC, csp_timeout);
                }
                //Get config
                else if(strcmp(key, "get_config") == 0)
                {
                    com_get_conf(&tnc_config, NODE_TNC, csp_timeout);
                    com_print_conf(&tnc_config);
                }
                //Get status
                else if(strcmp(key, "get_status") == 0)
                {
                    com_get_status(&tnc_config, NODE_TNC, csp_timeout);
                    com_print_status(&tnc_config);
                }
                //PING
                else if(strcmp(key, "ping") == 0)
                {
                    char *dest = json_string_value(value);
                    //ivalue = (uint8_t)json_integer_value(value);
                    
                    // Parse ping address
                    if(strcmp(dest, "obc") == 0)
                        ivalue = R_ADDRESS_OBC;
                    else if(strcmp(dest, "trx") == 0)
                        ivalue = R_ADDRESS_TRX;
                    else if(strcmp(dest, "tnc") == 0)
                        ivalue = R_ADDRESS_TNC;
                    else if(strcmp(dest, "gnd") == 0)
                        ivalue = R_ADDRESS_GND;
                    else
                        ivalue = 0xFF;
                    
                    // Send ping command
                    if(ivalue != 0xFF)
                    {
                        int result = csp_ping(ivalue, 5*csp_timeout, 10, CSP_O_NONE);
                        printf("Ping to %d of size %d took %d ms.\n", ivalue, 10, result);
                    }
                    else
                    {
                        printf("Invalid ping address: %s\n", dest);
                    }
                }
                else
                {
                    printf("Invalid tnc command\n");
                }
            }
        }
        //Not implemented message type
        else
        {
            printf("[Client] Invalid message\n");
        }
        
        json_decref(root);
        free(message);
    }
    
    zmq_close (receiver);
    zmq_ctx_destroy (context);

    return CSP_TASK_RETURN;
}

/**
 * Main function, initializes libcsp, serial kiss interface, task client and
 * task server.
 */
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

/*
 * nanocom.c
 *
 *  Created on: 14/01/2010
 *      Author: johan
 */

int com_set_conf(nanocom_conf_t * config, uint8_t node, uint32_t timeout) {
    config->morse_bat_level = csp_hton16(config->morse_bat_level);
    config->morse_pospone = csp_hton16(config->morse_pospone);
    config->morse_inter_delay = csp_hton16(config->morse_inter_delay);
    config->hk_interval = csp_hton16(config->hk_interval);
    config->preamble_length = csp_hton16(config->preamble_length);
    config->tx_max_temp = csp_hton16(config->tx_max_temp);
    return csp_transaction(CSP_PRIO_HIGH, node, COM_PORT_CONF, timeout, (void *) config, sizeof(nanocom_conf_t), NULL, 0);
}

int com_get_conf(nanocom_conf_t * config, uint8_t node, uint32_t timeout) {
    int status = csp_transaction(CSP_PRIO_HIGH, node, COM_PORT_CONF, timeout, NULL, 0, (void *) config, sizeof(nanocom_conf_t));
    if (status == 0)
        return 0;
    config->morse_bat_level = csp_ntoh16(config->morse_bat_level);
    config->morse_pospone = csp_ntoh16(config->morse_pospone);
    config->morse_inter_delay = csp_ntoh16(config->morse_inter_delay);
    config->hk_interval = csp_ntoh16(config->hk_interval);
    config->preamble_length = csp_ntoh16(config->preamble_length);
    config->tx_max_temp = csp_ntoh16(config->tx_max_temp);
    return status;
}

int com_restore_conf(uint8_t node) {
    return csp_transaction(CSP_PRIO_HIGH, node, COM_PORT_RESTORE, 0, NULL, 0, NULL, 0);
}

int com_get_status(nanocom_data_t * data, uint8_t node, uint32_t timeout) {
    int status = csp_transaction(CSP_PRIO_NORM, node, COM_PORT_STATUS, timeout, NULL, 0, (void *) data, sizeof(nanocom_data_t));
    if (status != sizeof(nanocom_data_t))
        return status;
    data->bit_corr_tot = csp_ntoh32(data->bit_corr_tot);
    data->byte_corr_tot = csp_ntoh32(data->byte_corr_tot);
    data->rx = csp_ntoh32(data->rx);
    data->rx_err = csp_ntoh32(data->rx_err);
    data->tx = csp_ntoh32(data->tx);
    data->last_rferr = csp_ntoh16(data->last_rferr);
    data->last_rssi = csp_ntoh16(data->last_rssi);
    data->last_temp_a = csp_ntoh16(data->last_temp_a);
    data->last_temp_b = csp_ntoh16(data->last_temp_b);
    data->last_txcurrent = csp_ntoh16(data->last_txcurrent);
    data->last_batt_volt = csp_ntoh16(data->last_batt_volt);
    data->bootcount = csp_ntoh32(data->bootcount);
    return status;
}

int com_get_log_rssi(nanocom_rssi_t * data, uint8_t * count, uint8_t node, uint32_t timeout) {
    int status = csp_transaction(CSP_PRIO_NORM, node, COM_PORT_LOG_RSSI, timeout, NULL, 0, (void *) data, -1);
    if (status == 0)
        return 0;
    if (status % sizeof(nanocom_rssi_t))
        return 0;
    unsigned int i;
    for (i = 0; i < status / sizeof(nanocom_rssi_t); i++) {
        nanocom_rssi_t * logd = data + i;
        logd->time = csp_ntoh32(logd->time);
        logd->rssi = csp_ntoh16(logd->rssi);
        logd->rferr = csp_ntoh16(logd->rferr);
    }
    *count = status / sizeof(nanocom_rssi_t);
    return 1;
}

int com_get_hk(nanocom_hk_t * data, uint8_t * count, uint8_t node, uint32_t timeout) {
    int status = csp_transaction(CSP_PRIO_NORM, node, COM_PORT_LOG_HK, timeout, NULL, 0, (void *) data, -1);
    if (status == 0)
        return 0;
    if (status % sizeof(nanocom_hk_t))
        return 0;
    unsigned int i;
    for (i = 0; i < status / sizeof(nanocom_hk_t); i++) {
        nanocom_hk_t * hkd = data + i;
        hkd->batt_volt = csp_ntoh16(hkd->batt_volt);
        hkd->temp_a = csp_ntoh16(hkd->temp_a);
        hkd->temp_b = csp_ntoh16(hkd->temp_b);
        hkd->time = csp_ntoh32(hkd->time);
    }
    *count = status / sizeof(nanocom_hk_t);
    return 1;
}

int com_get_calibration(uint8_t node, nanocom_calibrate_t * com_calibrate, uint32_t timeout) {
    int status = csp_transaction(CSP_PRIO_NORM, node, COM_PORT_CALIBRATE, timeout, NULL, 0, (void *) com_calibrate, sizeof(nanocom_calibrate_t));
    if (status == 0)
        return 0;
    com_calibrate->con_rferr = csp_ntoh16(com_calibrate->con_rferr);
    com_calibrate->raw_rferr = csp_ntoh16(com_calibrate->raw_rferr);
    com_calibrate->con_rssi = csp_ntoh16(com_calibrate->con_rssi);
    com_calibrate->raw_rssi = csp_ntoh16(com_calibrate->raw_rssi);
    return status;
}

int com_set_tx_inhibit(uint8_t node, uint8_t value, uint32_t timeout) {
    uint8_t ret;
    int status = csp_transaction(CSP_PRIO_HIGH, node, COM_PORT_TX_INHIBIT, timeout, &value, sizeof(value), &ret, sizeof(ret));
    if (status != sizeof(ret))
        return -1;
    return 0;
}

void com_print_conf(nanocom_conf_t * com_conf) {
    printf("FEC: rs %u, random %u, viterbi %u\r\n", com_conf->do_rs, com_conf->do_random, com_conf->do_viterbi);
    printf("RADIO: rx %u, tx %u, preamble %u, max temp: %d\r\n", com_conf->rx_baud, com_conf->tx_baud, com_conf->preamble_length, com_conf->tx_max_temp);
    printf("MORSE: enable: %u, mode: %u,  delay %u, pospone %u, wpm %u, batt level %u, text %s\r\n", com_conf->morse_enable, com_conf->morse_mode, com_conf->morse_inter_delay, com_conf->morse_pospone, com_conf->morse_wpm, com_conf->morse_bat_level, com_conf->morse_text);
    printf("MORSE: cycle: %u, volt:%u rxc:%u txc:%u tempa:%u tempb:%u rssi:%u rferr:%u\r\n", com_conf->morse_cycle, com_conf->morse_en_voltage, com_conf->morse_en_rx_count, com_conf->morse_en_tx_count, com_conf->morse_en_temp_a, com_conf->morse_en_temp_b, com_conf->morse_en_rssi, com_conf->morse_en_rf_err);
    printf("HK: interval %u\r\n", com_conf->hk_interval);
}

void com_print_status(nanocom_data_t * com_stat) {
        printf("Bits corrected total: %lu\r\n", com_stat->bit_corr_tot);
        printf("Bytes corrected total:  %lu\r\n", com_stat->byte_corr_tot);
        printf("RX packets:  %lu\r\n", com_stat->rx);
        printf("RX checksum errors:  %lu\r\n", com_stat->rx_err);
        printf("TX packets:  %lu\r\n", com_stat->tx);
        printf("Freq. Error:  %d\r\n", com_stat->last_rferr);
        printf("Last RSSI:  %d\r\n", com_stat->last_rssi);
        printf("Last A temp:  %d\r\n", com_stat->last_temp_a);
        printf("Last B temp:  %d\r\n", com_stat->last_temp_b);
        printf("Last TX current:  %d\r\n", com_stat->last_txcurrent);
        printf("Last Battery Voltage:  %d\r\n", com_stat->last_batt_volt);
        printf("Bootcount:  %lu\r\n", com_stat->bootcount);
}
