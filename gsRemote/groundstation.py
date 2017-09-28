#!/usr/bin/env python3
# -*- coding: latin-1 -*-

"""
                        SUCHAI Ground Station Software
            A remote interface to send commands and receive telemetry

      Copyright 2017, Carlos Gonzalez Cortes, carlgonz@uchile.cl
      Copyright 2017, Camilo Rojas Milla, camrojas@uchile.cl

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import datetime
import json
import re
import os
from collections import OrderedDict

from pymongo import MongoClient

from PyQt4.Qt import *
from PyQt4 import QtGui
from PyQt4 import QtCore

from forms.Console import Ui_MainWindow
from forms.EditCommandDialog import Ui_DialogEditCommandList

from client import Client
from telemetry import Telemetry


config_path = "/usr/share/groundstation/"
local_config_path = os.path.expanduser("~/.config/groundstation")
if not os.path.exists(config_path):
    config_path = "/usr/local/share/groundstation/"
    if not os.path.exists(config_path):
        config_path = "config/"
    else:
        print("Warning: no application path found")

if not os.path.exists(local_config_path):
    import shutil
    print("No local config path. Creating")
    os.mkdir(local_config_path)
    shutil.copy(os.path.join(config_path, "config.json"), local_config_path)


class SerialCommander(QtGui.QMainWindow):
    """
    Main class, creates and configures main window. Also sets signals and
    slots.
    """
    # Signals
    _new_char = pyqtSignal(type(""))  # New char signal

    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        # Instance variables
        self.client = None
        self.alive = False
        self.receiver_thread = None
        self.history = []
        self.history_cnt = 0
        self.tc_history = {}
        self.tc_history_cnt = 0
        self.timestamp = False

        # Load version
        self.version = "0.0.0"
        try:
            with open(os.path.join(config_path, "version.txt")) as ver_file:
                self. version = ver_file.readline()
        except IOError:
            print("Version file not found")
            pass

        # Load config
        try:
            config_file = open(os.path.join(local_config_path, "config.json"), 'r')
            self.config = json.load(config_file)
            config_file.close()
        except IOError:
            self.config = {}

        # Load telecommands list
        try:
            tc_set = set()  # Avoid duplicated items
            tc_file = open(os.path.join(config_path,"cmd_list.txt"), 'r')

            for line in tc_file:
                line = line.replace(',', ', ')
                line = line.replace('\n', '')
                tc_set.add(line)

            tc_file.close()

            tc_list = list(tc_set)
            tc_list.sort()
            self.config["tc_list"] = tc_list

        except IOError as e:
            print(e)
            self.config["tc_list"] = []

        self.commands_list = self.config.get("commands", [])

        # Set mongo DB
        db_server = self.config.get("db_server", "localhost")
        db_port = self.config.get("db_port", 27017)
        self.mongo_client = MongoClient(db_server, db_port)

        # Set GUI
        self.window = Ui_MainWindow()
        self.window.setupUi(self)
        self.window.tabWidget.setCurrentIndex(0)
        self.setup_comm()
        self.setup_send()
        self.setup_actions()
        self.setup_telecommands()
        self.setup_telemetry()

        # Set Telemetries to be stored
        self.telemetries = OrderedDict()
        self.update_telemetry_array()

    def setup_comm(self):
        """
        Sets connections combobox.
        """
        # Connections
        self.window.pushButtonOpenPort.clicked.connect(self.open_connection)
        self.window.pushButtonClosePort.clicked.connect(self.close_connection)

        self.window.tableWidgetTelemetry.itemClicked.connect(self.visualize)

        # Hosts
        available_hosts = self.config.get("hosts", ["", ])
        self.window.lineEditURL.setText(available_hosts[0])

        # Ports
        available_ports_send = self.config.get("ports_send", ["", ])
        available_ports_send.reverse()
        self.window.comboBoxPortSend.addItems(available_ports_send)
        available_ports_recv = self.config.get("ports_recv", ["", ])
        available_ports_recv.reverse()
        self.window.comboBoxPortRecv.addItems(available_ports_recv)

        self.timestamp = self.window.checkBoxTimestamp.isChecked()

    def setup_send(self):
        """
        Config cmd send and selection window
        """
        # Add command list
        self.window.listWidgetCommand.addItems(self.commands_list)

        # Connections
        self.window.listWidgetCommand.itemDoubleClicked.connect(self.command_clicked)
        self.window.pushButtonSend.clicked.connect(self.send_msg)
        self.window.checkBoxTimestamp.toggled.connect(self.timestamp_toggle)

    def setup_actions(self):
        """
        Config toolbar menus
        """
        self.window.actionGuardar.triggered.connect(self.save_log)
        self.window.actionAgregar_comando.triggered.connect(self.add_cmd)
        self.window.actionAcerca_de.triggered.connect(self.about)

    def about(self):
        msg = "Version {}".format(self.version)
        QtGui.QMessageBox.information(self, "About", msg, QtGui.QMessageBox.Ok)
        return

    def setup_telecommands(self):
        """
        Configures telecommands tab
        """
        # Fill telecommand list
        cmd_list = self.config.get("tc_list")
        if cmd_list:
            self.window.listWidget_cmd.addItems(cmd_list)

        # Connections
        self.window.lineEdit_tcfilter.textChanged.connect(self.tc_filter)
        self.window.listWidget_cmd.itemDoubleClicked.connect(self.tc_addtoframe)
        self.window.pushButton_tcclear.clicked.connect(self.tc_clearframe)
        self.window.pushButton_tcsend.clicked.connect(self.tc_send)
        # self.window.pushButton_tlsave.clicked.connect(self.tl_save)
        self.window.pushButton_tldelete.clicked.connect(self.tl_delete)
        self.window.pushButton_tltocsv.clicked.connect(self.tl_csv)
        self.window.pushButton_tlimport.clicked.connect(self.tl_import)
        self.window.pushButton_tcdelete.clicked.connect(self.tc_delete)
        self.window.comboBox_tchistory.activated.connect(self.tc_load_hist)

    def setup_telemetry(self):
        db_server = self.config.get("db_server", "127.0.0.1")
        db_port = self.config.get("db_port", 27017)
        self.window.lineEdit_dbserver.setText(db_server)
        self.window.lineEdit_dbport.setText(str(db_port))
        self.window.tableWidgetTelemetry.setColumnHidden(8, True)  # Hide _id
        self.window.pushButton_dbconnect.clicked.connect(self.tl_reconnect_db)

    def tc_filter(self, text):
        """
        Filters telecommand list by text
        """
        if len(text):
            f_list = [s for s in self.config.get("tc_list") if str(text) in s]
            self.window.listWidget_cmd.clear()
            self.window.listWidget_cmd.addItems(f_list)
        else:
            self.window.listWidget_cmd.clear()
            self.window.listWidget_cmd.addItems(self.config.get("tc_list"))

    def tc_addtoframe(self, item):
        """
        Add new tc in item to current frame
        """
        tc_text = str(item.text())
        [cmd, name] = tc_text.split(',')
        item_cmd = QTableWidgetItem(cmd)
        item_name = QTableWidgetItem(name)
        item_par = QTableWidgetItem('0')

        rows = self.window.tableWidget_tcframe.rowCount()
        self.window.tableWidget_tcframe.setRowCount(rows+1)
        self.window.tableWidget_tcframe.setItem(rows, 0, item_name)
        self.window.tableWidget_tcframe.setItem(rows, 1, item_cmd)
        self.window.tableWidget_tcframe.setItem(rows, 2, item_par)
        self.window.tableWidget_tcframe.resizeColumnToContents(0)

    def tc_clearframe(self, item):
        """
        Clears current tc frame
        """
        self.window.tableWidget_tcframe.clearContents()
        self.window.tableWidget_tcframe.setRowCount(0)

    def tc_send(self):
        """
        Send current tc frame
        """
        tc_frame = []
        tmp_tc_frame = []
        cmd_stop = 0xfffe
        rows = self.window.tableWidget_tcframe.rowCount()

        for i in range(rows):
            item = self.window.tableWidget_tcframe.item(i, 1)
            tc = int(str(item.text()), 16)
            tc_frame.append(tc)

            item = self.window.tableWidget_tcframe.item(i, 2)
            value = int(str(item.text()), 10)
            tc_frame.append(value)

            item = self.window.tableWidget_tcframe.item(i, 0)
            name = str(item.text())

            # Add command line to hist
            cmd_par = (name, tc, value)
            tmp_tc_frame.append(cmd_par)

        # Send frame to history
        self.tc_add_hist(tmp_tc_frame)

        tc_frame.append(cmd_stop)
        tc_frame.append(cmd_stop)

        tc_json = {"type": "tc",
                   "data": tc_frame}

        tc_msj = json.dumps(tc_json)
        self.client.send(tc_msj)

    def tc_delete(self):
        """
        Delete selected TC row
        """
        item = self.window.tableWidget_tcframe.currentRow()
        self.window.tableWidget_tcframe.removeRow(item)

    def tc_add_hist(self, frame):
        """
        Add TC frame to history
        """
        ts = datetime.datetime.now().isoformat(' ')
        self.tc_history[ts] = frame
        self.window.comboBox_tchistory.addItem(ts)

    def tc_load_hist(self, item):
        """
        Load selected frame from history to table
        """
        ts = self.window.comboBox_tchistory.currentText()
        frame = self.tc_history[ts]
        self.tc_clearframe(None)

        for row in frame:
            item_name = QTableWidgetItem(str(row[0]))
            item_cmd = QTableWidgetItem(hex(row[1]))
            item_par = QTableWidgetItem(str(row[2]))

            rows = self.window.tableWidget_tcframe.rowCount()
            self.window.tableWidget_tcframe.setRowCount(rows+1)
            self.window.tableWidget_tcframe.setItem(rows, 0, item_name)
            self.window.tableWidget_tcframe.setItem(rows, 1, item_cmd)
            self.window.tableWidget_tcframe.setItem(rows, 2, item_par)

    def timestamp_toggle(self, value):
        """
        Slot to toggle timestamp in console text
        """
        self.timestamp = value

    def add_cmd(self):
        """
        Edit command list
        """
        dialog = EditCommandDialog(self,self.commands_list)
        self.commands_list = dialog.run_tool()
        self.config["commands"] = self.commands_list

        self.window.listWidgetCommand.clear()
        self.window.listWidgetCommand.addItems(self.commands_list)

    def write_terminal(self, text):
        """
        Log received msg to terminal
        """
        text = text.replace('\n', '')
        text = text.replace('\r', '')

        # Separate msg fields. If fail, just copy the text
        try:
            msg = json.loads(text)
            typ = msg.get("type", "other")
            data = msg.get("data", text)
            log = "[{0}] {1}\n".format(typ, data)
        except:
            typ = "debug"
            data = text
            log = "[{0}] {1}\n".format(typ, data)

        # Moves cursor to end
        c = self.window.textEditTerminal.textCursor()
        c.movePosition(QTextCursor.End)
        self.window.textEditTerminal.setTextCursor(c)

        if self.timestamp:
            # Add timestamp
            ts = datetime.datetime.now().isoformat(' ')
            log = '[{0}]{1}'.format(ts, log)

        # Normal mode, just write text in terminal
        self.window.textEditTerminal.insertPlainText(log)

        c.movePosition(QTextCursor.End)
        self.window.textEditTerminal.setTextCursor(c)

        # Process special msgs
        if typ == "tm":
            self._process_tm(data)

    def _process_tm(self, data):
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%y-%m-%d %H:%M:%S")
        # Fix data ending with commands (Issue #4)
        # This fix was added for compatibily with versions < 0.4.6 and can
        # be removed in the future
        if data[-1] == "," or data[-1] == "\n":
            data = data[:-1]
        # Split comma separated values
        data = data.split(',')

        # 1. Parse frames
        # Header in all frames
        t_frame = data[0]  # type of frame
        n_frame = data[1]  # number of frame

        # Header in all frames of type 0x1000 (Start) or 0x4000 (Simple)
        t_data = data[2]  # Type of payload

        # Header in payloads frames (not tm_estado) of type 0x1000 (Start)
        l_data = data[3]    # length of data
        p_status = data[4]  # payload status

        # 2. Parse data
        _data_start = data[5:]  # data in frames 0x1000 (Start) and 0x4000 (Simple)
        _data_conti = data[2:]  # data in frames 0x3000 (Conti) and 0x2000 (End)

        # 3. Build telemetry
        if t_frame == "0x0100" or t_frame == "0x0400":  # it is a new frame o 0x4000
            # First check if the last telemetry is alright
            if len(self.telemetries) != 0:
                # check if the last telemetry is finished
                key, last_tel = self.telemetries.popitem()
                if last_tel.get_state() != 2:
                    last_tel.set_state(3)  # broken
                self.telemetries[key] = last_tel

            # Append a new telemetry
            tel = Telemetry(date=ts)
            tel.set_payload(t_data)

            # Fix tm_estado simple vs tm_estado payload
            # HACK: in tm_estado simple l_data=data[3] is the first data in the
            # frame and can be only 0 or 1, but in tm_estado payload l_data is a
            # big number > 1
            is_simple_estado = tel.get_payload() == 0 and int(l_data, 16) <= 1

            # Case simple tm_estado frame
            if is_simple_estado:
                tel.set_l_data("0x0001")
                tel.set_p_status("0x0004")
                # Fix tm_estado simple header to match payload format
                # Add dummy [Time1,Time2]
                tel.set_data(["0x0000", "0x0000"] + data[3:], n_frame)
            # Case normal payload frame
            else:
                tel.set_l_data(l_data)
                tel.set_p_status(p_status)
                tel.set_data(_data_start, n_frame)

            # Change status to received more frames
            if t_frame == "0x0400":
                tel.set_state(2)  # Finished status
            else:
                tel.set_state(1)  # Ongoing status

            # Save current telemetry to DB
            tel.save(self.mongo_client)
            self.telemetries[tel.get_obj_id()] = tel

        elif t_frame == "0x0200":  # it is an ending frame
            if len(self.telemetries) != 0:  # if this is not true something is wrong
                key, tel = self.telemetries.popitem()
                tel_state = tel.get_state()

                # if the last frame was in progress (1) mark as finished,
                # add new data and return element to list
                if tel_state == 1:
                    tel.set_state(2)  # mark finished
                    tel.set_data(_data_conti, n_frame)
                    tel.save(self.mongo_client)
                    self.telemetries[key] = tel

                # if the last frame was finished, create a new one marked as
                # broken and store in the list
                elif tel_state == 2:
                    tel = Telemetry(date=ts)
                    tel.set_data(_data_conti, n_frame)
                    tel.set_state(3)  # Mark broken
                    tel.save(self.mongo_client)
                    self.telemetries[tel.get_obj_id()] = tel

                # other cases (borken, empty, etc), mark as broken, add new data
                # and restore element to list
                else:
                    tel.set_state(3)  # mark broken
                    tel.set_data(_data_conti, n_frame)
                    tel.save(self.mongo_client)
                    self.telemetries[key] = tel

        elif t_frame == "0x0300":  # it is an ongoing frame
            if len(self.telemetries) != 0:  # if this is not true something is wrong
                key, tel = self.telemetries.popitem()
                if tel.get_state() in (1, 3):  # In progress or broken
                    tel.set_data(_data_conti, n_frame)  # Update
                    tel.save(self.mongo_client)  # Save
                    self.telemetries[key] = tel  # Return to list

                else:  # tel.get_state() == 2:  # last frame has finished
                    tel = Telemetry(date=ts)  # New
                    tel.set_data(_data_conti, n_frame)  # Update
                    tel.set_state(3)  # Mark as broken
                    tel.save(self.mongo_client)  # Save
                    self.telemetries[tel.get_obj_id()] = tel  # Add to list

        self.update_telemetry_table()

    def update_telemetry_array(self):
        if len(self.mongo_client.nodes) > 0:
            db = self.mongo_client.suchai1_tel_database
            names = db.collection_names()
            for i in range(0, len(names)):
                payloads = list(Telemetry.dictPayload.keys())
                for j in range(0, len(payloads)):
                    if names[i] == payloads[j]:
                        self.update_telemetry_from_collection(Telemetry.get_collection_with_payload(self.mongo_client, Telemetry.dictPayload[payloads[j]]))
            self.update_telemetry_table(sort=True)

    def update_telemetry_from_collection(self, collection):
        cursor = collection.find()
        for document in cursor:
            tel = self.document_to_telemetry(document)
            self.telemetries[tel.get_obj_id()] = tel

    def document_to_telemetry(self, doc):
        tel = Telemetry()
        tel.set_state(doc['state'])
        tel.set_doc_payload(doc["payload"])
        tel.set_doc_data(doc["data"])
        tel.set_n_data(doc["n_data"])
        tel.set_lost_p(doc["lost_p"])
        tel.set_l_data(doc["l_data"])
        tel.set_p_status(doc["p_status"])
        tel.set_obj_id(doc['_id'])
        id_timestamp = doc["_id"].generation_time.strftime("%y-%m-%d %H:%M:%S")
        tel.set_date(doc.get("date", id_timestamp))  # Compatible with < 0.4.6
        return tel

    def update_telemetry_table(self, sort=False):
        self.window.tableWidgetTelemetry.clearContents()
        self.window.tableWidgetTelemetry.setRowCount(0)
        # Disable sorting before editing table, prevent bugs
        self.window.tableWidgetTelemetry.setSortingEnabled(False)

        for i, tel in enumerate(self.telemetries.values()):
            self.window.tableWidgetTelemetry.insertRow(i)
            self.window.tableWidgetTelemetry.setItem(i, 0, QtGui.QTableWidgetItem(tel.get_date()))
            self.window.tableWidgetTelemetry.setItem(i, 1, QtGui.QTableWidgetItem(tel.get_state_name()))
            self.window.tableWidgetTelemetry.setItem(i, 2, QtGui.QTableWidgetItem(tel.get_payload_name()))
            self.window.tableWidgetTelemetry.setItem(i, 3, QtGui.QTableWidgetItem(str(tel.get_n_data())))
            self.window.tableWidgetTelemetry.setItem(i, 4, QtGui.QTableWidgetItem(str(tel.get_lost_p())))
            self.window.tableWidgetTelemetry.setItem(i, 5, QtGui.QTableWidgetItem(tel.get_p_status()))
            self.window.tableWidgetTelemetry.setItem(i, 6, QtGui.QTableWidgetItem(str(tel.get_l_data())))
            self.window.tableWidgetTelemetry.setItem(i, 7, QtGui.QTableWidgetItem(','.join(tel.get_data())))
            self.window.tableWidgetTelemetry.setItem(i, 8, QtGui.QTableWidgetItem(str(tel.get_obj_id())))

        # Re-enable sorting after table was edited
        self.window.tableWidgetTelemetry.setSortingEnabled(True)
        self.window.tableWidgetTelemetry.resizeColumnToContents(0)
        if sort:
            self.window.tableWidgetTelemetry.sortByColumn(0, Qt.AscendingOrder)

    def visualize(self, item):
        obj_id = self.window.tableWidgetTelemetry.item(item.row(), 8)  # ID
        self.window.textEditTelemetry.setPlainText(self.telemetries[obj_id.text()].to_string())

    def tl_reconnect_db(self):
        """
        Slot to reconnect to a different mongoDB. IP:PORT are read from GUI.
        :return: None
        """
        from pymongo.errors import ConnectionFailure

        db_server = self.window.lineEdit_dbserver.text()
        db_port = int(self.window.lineEdit_dbport.text())
        new_client = MongoClient(db_server, db_port)

        # Test connection
        try:
            self.window.statusbar.showMessage("Connecting to database...")
            app.setOverrideCursor(Qt.WaitCursor)
            new_client.admin.command('ismaster')
        except ConnectionFailure:
            print("Server not available")
            # Show a confirmation message
            err_msg = "Unable to connect to database {}:{}".format(db_server, db_port)
            app.restoreOverrideCursor()
            self.window.statusbar.showMessage(err_msg, 2000)
            QtGui.QMessageBox.critical(self, "Error", err_msg, QtGui.QMessageBox.Ok)
            return

        # If everything is Ok, close old connection and replace dB
        self.config["db_server"] = db_server
        self.config["db_port"] = db_port
        self.window.statusbar.showMessage("Connected {}:{}!".format(db_server, db_port), 5000)
        self.mongo_client.close()
        self.mongo_client = new_client
        # Re-load telemetry table
        self.telemetries.clear()
        self.update_telemetry_array()
        app.restoreOverrideCursor()

    def tl_save(self):
        for tel in self.telemetries.values():
            tel.save(self.mongo_client)

    def tl_delete(self):
        # Show a confirmation message
        ret = QtGui.QMessageBox.warning(self, "Warning",
                                        "Do you really want to delete the entry?\n"
                                        "This action cannot be undone.",
                                        QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok,
                                        QtGui.QMessageBox.Cancel)
        # Do nothing if user cancels
        if ret == QtGui.QMessageBox.Cancel:
            return
        # Actually remove the element
        else:
            rows = [item.row() for item in self.window.tableWidgetTelemetry.selectedItems()]
            id_items = [self.window.tableWidgetTelemetry.item(row, 8) for row in set(rows)]
            for obj_id in id_items:
                obj_id = obj_id.text()
                tel = self.telemetries.pop(obj_id)
                tel.delete(self.mongo_client)
            self.update_telemetry_table()

    def tl_csv(self):
        rows = [item.row() for item in self.window.tableWidgetTelemetry.selectedItems()]
        id_items = [self.window.tableWidgetTelemetry.item(row, 8) for row in set(rows)]
        telemetries = [self.telemetries[id_item.text()] for id_item in id_items]
        name = QtGui.QFileDialog.getSaveFileName(self, "Save File", QDir.currentPath(), "CSV files (*.csv);;Text files (*.txt);;All files (*.*)")
        telemetries[0].to_csv(name)

    def tl_import(self):
        name = QtGui.QFileDialog.getOpenFileName(self, 'Open File')
        if name:
            app.setOverrideCursor(Qt.BusyCursor)
            self.tl_parse_log(name)
            app.restoreOverrideCursor()

    def tl_parse_log(self, log_path):
        file = open(log_path)

        for line in file:
            if re.match(r'(.*)Prueba(.*?).*', line):
                # print("Start Test")
                continue

            elif re.match(r'(.*)exe_cmd(.*?).*', line):
                print(line)

            elif len(line) != 0 and re.search(r'\[tm\].*', line) != None:
                print(line)
                data = re.sub(r'\[.*\]\[tm\] ', '' , line).split(',')
                # print(data)
                if len(data) > 1:
                    # data[0] = data[0][5:]
                    if data[-1] == '\n':
                        del data[-1]
                    print(data)
                    self._process_tm(','.join(data))

        file.close()

    def command_clicked(self, item):
        """
        Move a command from the list to text entry
        """
        self.window.lineEditSend.setText(item.text())

    def open_connection(self):
        """
        Opens connection with server indicated in GUI
        """
        self.window.pushButtonClosePort.setEnabled(True)
        self.window.pushButtonOpenPort.setEnabled(False)
        self.window.pushButtonSend.setEnabled(True)

        url_server = self.window.lineEditURL.text()
        recv_port = self.window.comboBoxPortRecv.currentText()
        send_port = self.window.comboBoxPortSend.currentText()

        try:
            self.client = Client(url_server, send_port, recv_port)
            self.client.new_message.connect(self.write_terminal)
            self.alive = True
        except Exception as e:
            QMessageBox.critical(self, 'Error', 'Error al abrir el puerto serial\n'+str(e))
            self.close_connection()

    def close_connection(self):
        """
        Close connections
        """
        self.window.pushButtonClosePort.setEnabled(False)
        self.window.pushButtonOpenPort.setEnabled(True)
        self.window.pushButtonSend.setEnabled(False)
        self.alive = False
        self.client = None

    def send_msg(self):
        """
        Send written message to server
        """
        msg = str(self.window.lineEditSend.text())
        self.add_history(msg)

        # Add LF y/o CR
        if self.window.checkBoxLF.isChecked():
            msg += '\n'
        if self.window.checkBoxCR.isChecked():
            msg += '\r'

        self.client.send(msg)
        self.window.lineEditSend.clear()
        self.history_cnt = 0

    def save_log(self):
        """
        Saves terminal content to file
        """
        doc_file = QFileDialog.getSaveFileName(self, "Guardar archivo", QDir.currentPath(), "Archivos de texto (*.txt);;All files (*.*)")
        doc_file = str(doc_file)
        document = self.window.textEditTerminal.document()
        m_write = QTextDocumentWriter()
        m_write.setFileName(doc_file)
        m_write.setFormat("txt")
        m_write.write(document)

    def add_history(self, line):
        """
        Adds a new line to history. Deletes old entries if more than 100
        messages exist.
        """
        if len(self.history) > 100:
            self.history.pop()

        try:
            if not (line == self.history[-1]):
                self.history.append(line)
        except:
            self.history.append(line)

    def get_history(self, index):
        """
        Returns the history index entry
        """
        if 0 < index <= len(self.history):
            return self.history[-index]
        else:
            return ''

    def history_send(self):
        """
        Add one line of the history to the send text entry
        """
        if self.history_cnt >= 0:
            if self.history_cnt > len(self.history):
                self.history_cnt = len(self.history)

            text = self.get_history(self.history_cnt)
            self.window.lineEditSend.setText(text)
        else:
            self.history_cnt = 0

    def closeEvent(self, event):
        """
        Does a clean exit. Close ports, stop threads and save command list.
        """
        # Close connections
        if self.alive:
            self.close_connection()
        self.mongo_client.close()
        # Save config
        config_filename = os.path.join(local_config_path, "config.json")
        with open(config_filename, "w") as config_file:
            json.dump(self.config, config_file, indent=4)
        # Close application
        event.accept()

    def keyPressEvent(self, event):
        """
        Manage key events
        """
        if event.key() == QtCore.Qt.Key_Up:
            if self.window.lineEditSend.hasFocus():
                self.history_cnt += 1
                self.history_send()

        if event.key() == QtCore.Qt.Key_Down:
            if self.window.lineEditSend.hasFocus():
                self.history_cnt -= 1
                self.history_send()

        # event for telemetry simulation
        if event.key() == QtCore.Qt.Key_T:
           self.tl_parse_log(sys.argv[1])

        # Events to change current tab
        if event.key() == QtCore.Qt.Key_1:
            if event.modifiers() & Qt.ControlModifier:
                self.window.tabWidget.setCurrentIndex(0)
        if event.key() == QtCore.Qt.Key_2:
            if event.modifiers() & Qt.ControlModifier:
                self.window.tabWidget.setCurrentIndex(1)
        if event.key() == QtCore.Qt.Key_3:
            if event.modifiers() & Qt.ControlModifier:
                self.window.tabWidget.setCurrentIndex(2)

        event.accept()


class EditCommandDialog(QtGui.QDialog):
    """
    Tool to edit command list
    """
    def __init__(self, parent=None, cmd_list=()):

        QtGui.QDialog.__init__(self, parent)

        self.ventana = Ui_DialogEditCommandList()
        self.ventana.setupUi(self)

        self.cmd_list = cmd_list
        self.ventana.listWidgetCommand.addItems(self.cmd_list)

        # Connections
        self.ventana.pushButtonDelete.clicked.connect(self.delete_item)
        self.ventana.pushButtonAdd.clicked.connect(self.add_item)

    def run_tool(self):
        """
        Opens dialog so user can add edit the list. Save changes and returns
        the new list at close.
        """
        ret = super(EditCommandDialog, self).exec_()
        if ret:
            self.cmd_list = []
            for row in range(self.ventana.listWidgetCommand.count()):
                item = self.ventana.listWidgetCommand.item(row)
                self.cmd_list.append(item.text())

        return self.cmd_list

    def delete_item(self):
        """
        Delete selected items
        """
        for item in self.ventana.listWidgetCommand.selectedItems():
            row = self.ventana.listWidgetCommand.row(item)
            witem = item = self.ventana.listWidgetCommand.takeItem(row)
            del witem

    def add_item(self):
        """
        Adds new item
        """
        cmd = self.ventana.lineEditAdd.text()
        self.ventana.listWidgetCommand.addItem(cmd)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    gui = SerialCommander()
    gui.show()
    sys.exit(app.exec_())
