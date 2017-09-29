import pymongo
import numpy as np
import pandas as pd
import datetime
from bson.objectid import ObjectId


class Telemetry(object):

    dictState = {
        0: "Empty",
        1: "In Progress",
        2: "Finished",
        3: "Broken",
        None: "Unkown"
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
        "expFis": 8,
        "unknown": -1
    }

    dictPayloadName = {
        0: "Status",
        1: "Battery",
        2: "Debug",
        3: "LangmuirProbe",
        4: "Gps",
        5: "Camera",
        6: "Temperature",
        7: "Gyroscope",
        8: "Physics",
        -1: "Unknown"
    }

    dictPayStatus = {
        0: "Inactive",
        1: "Active",
        2: "Init",
        3: "Take",
        4: "Stop",
        5: "Waiting download"
    }

    # payloadList = list(dictPayload.keys())

    def __init__(self, date=None):
        self.obj_id = None
        self.date = date
        self.data = []
        self.n_data = 0
        self.last_frame = -1
        self.lost_p = 0
        self.l_data = -1
        self.payload = None
        self.p_status = None
        self._dataframe = None

        # state of the telemetry
        #    0 -> empty
        #    1 -> in progress
        #    2 -> finished
        #    3 -> broken
        self.state = 0

    def append_hex(self, a, b):
        sizeof_b = 0
        # get size of b in bits
        while ((b >> sizeof_b) > 0):
            sizeof_b += 1
        # align answer to nearest 4 bits (hex digit)
        sizeof_b += sizeof_b % 4
        return (a << sizeof_b) | b


    def decode_time(self, time1, time2):

        date_time = int('0x' + time2[2:6]+time1[2:6], 16)
        year = (date_time&0b11111100000000000000000000000000)>>26
        month = (date_time&0b00000011110000000000000000000000)>>22
        day = (date_time&0b00000000001111100000000000000000)>>17
        hour = (date_time&0b00000000000000011111000000000000)>>12
        min =  (date_time&0b00000000000000000000111111000000)>>6
        sec = (date_time&0b00000000000000000000000000111111)>>0

        try:
            return datetime.datetime(year=year+2000, month=month, day=day, hour=hour, minute=min, second=sec)
        except ValueError:
            return '0x' + time2[2:6]+time1[2:6]


    def get_state(self):
        return self.state

    def get_state_name(self):
        return self.dictState.get(self.state, "-")
    
    def set_state(self, st):
        self.state = st

    def set_date(self, date):
        self.date = date

    def get_date(self):
        return self.date

    def set_obj_id(self, id):
        self.obj_id = id

    def get_obj_id(self):
        return str(self.obj_id)
    
    def get_data(self):
        return self.data

    def set_doc_data(self, dat):
        self.data = dat
        
    def set_data(self, dat, n_frame):
        self.data = self.data + dat
        
        if int(n_frame, 16) != self.last_frame+1:
            # self.lost_p = self.lost_p  + (int(n_frame, 16) - self.last_frame+1) uncomment when bug has been fixed
            # print str(int(n_frame, 16)) + " " +  str(self.last_frame+1)
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
        try:
            self.l_data = int(l_data, 16)
        except (ValueError, TypeError):
            self.l_data = l_data
        
    def get_payload(self):
        return self.payload

    def get_payload_name(self):
        return self.dictPayloadName.get(self.payload, "Unknown")

    def get_payload_string(self):
        return self.dictPayload[self.payload]

    def set_doc_payload(self, pay):
        if pay == 'None':
            self.payload = None
        else:
            self.payload = pay

    def set_payload(self, pay):
        self.payload = int(pay, 16)
        
    def get_p_status(self):
        return self.dictPayStatus.get(self.p_status, self.p_status)
    
    def set_p_status(self, p_status):
        try:
            self.p_status = int(p_status, 16)
        except (ValueError, TypeError):
            self.p_status = p_status

    def set_n_data(self, n_data):
        self.n_data = n_data

    def set_lost_p(self, lost_p):
        self.lost_p = lost_p

    def to_dict(self):
        return {
                "state": self.state,
                "payload": self.payload,
                "data": self.data,
                "n_data": self.n_data,
                "lost_p": self.lost_p,
                "l_data": self.l_data,
                "p_status": self.p_status,
                "date": self.date
                }

    def to_dataframe(self):
        if self.payload == self.dictPayload["gyro"]:
            step = 5  # One sample every 5 values
            maxl = (len(self.data) // step) * step  # Fix invalid len
            data = np.array(self.data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data)
            data.columns = ["time1", "time2", "X", "Y", "Z"]
            try:
                for i in data.columns[2:]:
                    data[i] = data[i].apply(lambda x: int(x, 16))
                data[["X", "Y", "Z"]] = data[["X", "Y", "Z"]].astype("int16")
            except Exception as e:
                print(e)

            data['time1'] = data.apply(lambda row: self.decode_time(row[0], row[1]), axis=1)
            data.drop('time2',1, inplace=True)
            data.rename(columns={'time1': 'time'}, inplace=True)
            self._dataframe = data

        elif self.payload == self.dictPayload["lagmuirProbe"]:
            """
            Langmuir will send 12 bytes, current message format:
                43 43 43 05 (3Bytes header + 1Byte ID Plasma)
                XX XX 		(2 byte Sweep Voltage: 4V)
                YY YY 		(2 byte Plasma Voltage)
                TT TT 		(2 byte Temperature ºK)
                ZZ ZZ 		(2 byte Particle Counter)
                
            Payload format is:
            [Header][CAL1][Header][CAL2][Header][CAL3][Header][CAL4]
            [Header][TIME][Header][Plasma] ... [TIME][Header][Plasma]
            ...
            [Header][CAL1][Header][CAL2][Header][CAL3][Header][CAL4][STOP][END]
            """
            step = 14  # One sample every 12 values
            data = self.data.copy()

            # Add some extra values between CAL packets to match the format of
            # plasma samples that are [date][sample]
            data.insert(14, data[1]); data.insert(14, data[0])
            data.insert(28, data[1]); data.insert(28, data[0])
            data.insert(42, data[1]); data.insert(42, data[0])

            def fix_missing(_data):
                """
                Fix some missing packets inside langmuir data. The standard
                format is [date+time][header+data]. If the lanmguir lost some
                data packets, this result in [date+time][date+time][header+data]
                samples inside the whole data frame. We need to remove the
                [date+time] of lost packets to match the general data format.
                :param _data: reference data frame
                :return: None. Modifies _data
                """
                # First is in i=2
                _i = 2
                _next = 14
                _start = "0x0043"
                while _i < len(_data):
                    if _data[_i] == _start:
                        # Data is Ok, look next packet
                        _i += _next
                    else:
                        # Oops not header found... go back and retry
                        del _data[_i-1]
                        del _data[_i-1]

            # Add some extra values between ending CAL packets to match the
            # format of plasma samples that are [date][sample]
            last_value = data.index("0xFFFE", len(data)//2) - 50
            data.insert(last_value+14, data[last_value+1]); data.insert(last_value+14, data[last_value+0])
            data.insert(last_value+28, data[last_value+1]); data.insert(last_value+28, data[last_value+0])
            data.insert(last_value+42, data[last_value+1]); data.insert(last_value+42, data[last_value+0])

            fix_missing(data)
            maxl = (len(data) // step) * step  # Fix invalid len
            data = np.array(data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data)
            data.columns = ["time1", "time2", "S1", "S2", "S3", "ID", "V1", "V2", "P1", "P2", "T1", "T2", "G1", "G2"]
            try:
                data["time"] = data.apply(lambda row: self.decode_time(row[0], row[1]), axis=1)
                data["header"] = data[["S1", "S2", "S3", "ID"]].apply(lambda x: "0x"+"".join(x).replace("0x00", ""), axis=1)
                data["Sweep voltage"] = data[["V1", "V2"]].apply(lambda x: "0x"+"".join(x).replace("0x00", ""), axis=1)
                data["Plasma voltage"] = data[["P1", "P2"]].apply(lambda x: "0x"+"".join(x).replace("0x00", ""), axis=1)
                data["Plasma temperature"] = data[["T1", "T2"]].apply(lambda x: "0x"+"".join(x).replace("0x00", ""), axis=1)
                data["Particles counter"] = data[["G1", "G2"]].apply(lambda x: "0x"+"".join(x).replace("0x00", ""), axis=1)
                data.drop(["time1", "time2", "S1", "S2", "S3", "ID", "V1", "V2", "P1", "P2", "T1", "T2", "G1", "G2"], 1, inplace=True)

                # Parse to int
                valid = (data["header"] == "0x43434301") | (data["header"] == "0x43434302") | (data["header"] == "0x43434303") | (data["header"] == "0x43434304") | (data["header"] == "0x43434305")
                for i in data.columns[2:]:
                    data.loc[valid, i] = data.loc[valid, i].apply(lambda x: int(x, 16))

            except Exception as e:
                print(e)
            self._dataframe = data

        elif self.payload == self.dictPayload["sensTemp"]:
            """
            Temperatures:
                              [alive1][alive2][alive3][alive4]
                [time1][time2][temp 1][temp 2][temp 3][temp 4]
                
            Note that first 4 samples indicate if the sensors are working
            properly but don't have timestamp. We need to remove then or
            add some padding to match the format of other samples.
            """
            # Add 2 samples as padding
            data = self.data.copy()
            data.insert(0, "0x0000")
            data.insert(0, "0x0000")
            step = 6  # One sample every 6 values
            maxl = (len(data) // step) * step  # Fix invalid len
            data = np.array(data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data)
            data.columns = ["time1", "time2", "Temp1", "Temp2", "Temp3", "Temp4"]
            try:
                for i in data.columns[2:]:
                    data[i] = data[i].apply(lambda x: int(x, 16))
                data[["Temp1", "Temp2", "Temp3", "Temp4"]] = data[["Temp1", "Temp2", "Temp3", "Temp4"]].astype("int16")
                data.loc[1:, ["Temp1", "Temp2", "Temp3", "Temp4"]] *= 0.0625  # To C
            except Exception as e:
                print(e)

            data['time1'] = data.apply(lambda row: self.decode_time(row[0], row[1]), axis=1)
            data.drop('time2', 1, inplace=True)
            data.rename(columns={'time1': 'time'}, inplace=True)
            self._dataframe = data

        elif self.payload == self.dictPayload["tm_estado"]:
            step = 50+2  # One sample every 50 values
            maxl = (len(self.data) // step) * step  # Fix invalid len
            data = np.array(self.data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data.transpose())
            try:
                data.loc[0, :] = data.apply(lambda col: self.decode_time(col[0], col[1]), axis=0)
                data.insert(0, "Fields", self.statusList)
                data.drop(1, axis=0, inplace=True)
            except Exception as e:
                print(e)

            try:
                for i in data.columns[1:]:
                    data[i] = data[i].apply(lambda x: int(x, 16))
            except KeyError:
                pass
            except Exception as e:
                print(e)

            self._dataframe = data

        elif self.payload == self.dictPayload["battery"]:
            hex2int = lambda x: int(x, 16)
            step = 7  # One sample every 5 values
            maxl = (len(self.data) // step) * step  # Fix invalid len
            data = np.array(self.data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data)
            data.columns = ["time1", "time2", "Voltage", "I in", "I out", "Temp 1", "Temp 2"]

            try:
                for i in data.columns[2:]:
                    data[i] = data[i].apply(lambda x: int(x, 16))
            except KeyError:
                pass
            except Exception as e:
                print(e)

            data['time1'] = data.apply(lambda row: self.decode_time(row[0], row[1]), axis=1)
            data.drop('time2',1, inplace=True)
            data.rename(columns={'time1': 'time'}, inplace=True)

            self._dataframe = data

        elif self.payload == self.dictPayload["gps"]:
            """
            GPS data are string lines including \r\n example:
            $GNRMC,000000.00,V,,,,,,,,,,N*63\r\n$GNRMC,000000.00,V,,,,,,,,,,N*63
            So it is easy to join samples as string and split in lines
            """
            data = [chr(int(x, 16)) for x in self.data]  # Convert to string
            data = "".join(data).splitlines()  # Split in a list of lines
            self._dataframe = pd.DataFrame(data)  # Dataframe of strings

        elif self.payload == self.dictPayload["camera"]:
            """
            Camera is saved as bytes array file, then read and saved to a Image
            object
            """
            data = ["{}{}".format(val[2:4], val[4:6]) for val in self.data]
            data = bytes().fromhex(" ".join(data))
            self._dataframe = data

        elif self.payload == self.dictPayload["expFis"]:
            """
            Parsed as ints
            """
            data = pd.DataFrame(self.data)
            try:
                data[0] = data[0].apply(lambda x: int(x, 16))
            except KeyError:
                pass
            except Exception as e:
                print(e)
            self._dataframe = data

        else:
            self._dataframe = pd.DataFrame(self.data)

        return self._dataframe

    def to_csv(self, fname):
        if self._dataframe is None:
            self.to_dataframe()

        if self.payload == self.dictPayload["camera"]:
            from io import BytesIO
            from PIL import Image
            imgfile = BytesIO(self._dataframe)
            Image.open(imgfile).save(fname)
        else:
            self._dataframe.to_csv(fname, index=False)

    def to_string(self):
        try:
            return self.to_dataframe().to_string()
        except AttributeError:
            return str(self._dataframe)

    def save(self, client):
        if len(client.nodes) > 0:
            if self.n_data > 0:
                _dict = self.to_dict()
                try:
                    self.insert_or_update(_dict, self.get_collection(client))
                except pymongo.errors.DuplicateKeyError as e:
                    print("Duplicate Key: {0}".format(e))
                    print("data not saved")
                    return
        else:
            print("no connection")

    def delete(self, client):
        if len(client.nodes) > 0:
            self.delete_from_collection(self.get_collection(client))
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
                    return db.expFis
                else:
                    return db.unknown
        return None

    @staticmethod
    def get_collection_with_payload(client, pay):
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
                return db.expFis
            else:
                return db.unknown

        return None

    def insert_or_update(self, _dict, collection):
        if self.obj_id is not None:
            res = collection.find_one(ObjectId(self.obj_id))
            if res is not None:
                collection.update({'_id': ObjectId(self.obj_id)}, _dict, True)
                print("updated object")
        else:
            res = collection.insert_one(_dict)
            self.obj_id = res.inserted_id
            print("inserted object")

    def delete_from_collection(self, collection):
        if self.obj_id is not None:
            res = collection.remove(ObjectId(self.obj_id))
            if res is not None:
                print("removed object")

    statusList = [
        "Time1",
        "Time2",
        "sta_RTC_isAlive",
        "sta_TRX_isAlive",
        "sta_EPS_isAlive",
        "sta_MemEEPROM_isAlive",
        "sta_MemSD_isAlive",
        "sta_AntSwitch_isOpen",
        "sta_fpl_index",
        "sta_ppc_opMode",
        "sta_ppc_lastResetSource",
        "sta_ppc_hoursAlive",
        "sta_ppc_hoursWithoutReset",
        "sta_ppc_resetCounter",
        "sta_ppc_wdt",
        "sta_ppc_osc",
        "sta_ppc_MB_nOE_USB_nINT_stat",
        "sta_ppc_MB_nOE_MHX_stat",
        "sta_ppc_MB_nON_MHX_stat",
        "sta_ppc_MB_nON_SD_stat",
        "sta_dep_ant_deployed",
        "sta_dep_ant_tries",
        "sta_dep_year",
        "sta_dep_month",
        "sta_dep_week_day",
        "sta_dep_day_number",
        "sta_dep_hours",
        "sta_dep_minutes",
        "sta_dep_seconds",
        "sta_rtc_year",
        "sta_rtc_month",
        "sta_rtc_week_day",
        "sta_rtc_day_number",
        "sta_rtc_hours",
        "sta_rtc_minutes",
        "sta_rtc_seconds",
        "sta_eps_batt_temp_0",
        "sta_eps_batt_temp_1",
        "sta_eps_battery_voltage",
        "sta_eps_panel_current",
        "sta_eps_panel_voltage_1",
        "sta_eps_panel_voltage_2",
        "sta_eps_panel_voltage_3",
        "sta_eps_system_current",
        "sta_trx_opmode",
        "sta_trx_count_tm",
        "sta_trx_count_tc",
        "sta_trx_day_last_tc",
        "sta_trx_beacon_period",
        "sta_trx_beacon_bat_lvl",
        "sta_trx_rx_baud",
        "sta_trx_tx_baud"
    ]

