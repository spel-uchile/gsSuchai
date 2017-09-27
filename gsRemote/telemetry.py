import pymongo
import numpy as np
import pandas as pd
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

    def to_datafarme(self):
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

            self._dataframe = data

        elif self.payload == self.dictPayload["sensTemp"]:
            step = 6  # One sample every 5 values
            maxl = (len(self.data) // step) * step  # Fix invalid len
            data = np.array(self.data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data)
            data.columns = ["time1", "time2", "Temp1", "Temp2", "Temp3", "Temp4"]
            try:
                for i in data.columns[2:]:
                    data[i] = data[i].apply(lambda x: int(x, 16))
                data[["Temp1", "Temp2", "Temp3", "Temp4"]] = data[["Temp1", "Temp2", "Temp3", "Temp4"]].astype("int16")
                data[["Temp1", "Temp2", "Temp3", "Temp4"]] *= 0.0625  # To C
            except Exception as e:
                print(e)

            self._dataframe = data

        elif self.payload == self.dictPayload["tm_estado"]:
            step = 50+2  # One sample every 50 values
            maxl = (len(self.data) // step) * step  # Fix invalid len
            data = np.array(self.data[0:maxl])
            data = data.reshape((-1, step))
            data = pd.DataFrame(data.transpose())
            data.insert(0, "Fields", self.statusList)
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
            self.to_datafarme()

        if self.payload == self.dictPayload["camera"]:
            from io import BytesIO
            from PIL import Image
            imgfile = BytesIO(self._dataframe)
            Image.open(imgfile).save(fname)
        else:
            self._dataframe.to_csv(fname, index=False)

    def to_string(self):
        try:
            return self.to_datafarme().to_string()
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

