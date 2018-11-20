from telemetry import Telemetry
from pymongo import MongoClient


telemetries ={}

def update_telemetry_from_collection(collection):
    cursor = collection.find()
    for document in cursor:
        tel = document_to_telemetry(document)
        telemetries[tel.get_obj_id()] = tel


def document_to_telemetry(doc):
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


db_server = "localhost"
db_port = 27017
mongo_client = MongoClient(db_server, db_port)

db = mongo_client.suchai1_tel_database
names = db.collection_names()
for i in range(0, len(names)):
    payloads = list(Telemetry.dictPayload.keys())
    for j in range(0, len(payloads)):
        if names[i] == payloads[j]:
            update_telemetry_from_collection(Telemetry.get_collection_with_payload(mongo_client, Telemetry.dictPayload[payloads[j]]))

lagmuir_finished = []
lagmuir_others = []
for k in telemetries.keys():
    if telemetries[k].payload == Telemetry.dictPayload['lagmuirProbe']:
        if telemetries[k].state == 2:
            lagmuir_finished.append(telemetries[k])
        else:
            lagmuir_others.append(telemetries[k])

for tel in lagmuir_finished:
    df = tel.to_dataframe()
    if 'time' in df.columns and len(df['time']) > 0:
        date_string = (df.iloc[0]['time']).strftime("%Y-%m-%d_%H:%M:%S")
    else:
        date_string = date_string = 'empty_' + tel.date.replace(" ", '_')
    print(date_string)
    tel.to_csv("lagmuir_csv/" + date_string + '.csv')



with open('broken_list.txt', 'a') as broken_list:
    for tel in lagmuir_others:
        broken_list.write(tel.date + '\n')

# print((lagmuir_finished[0].to_dataframe().iloc[0]['time']).strftime("%Y-%m-%d %H:%M:%S"))
# print(telemetries)
print(len(lagmuir_finished))
print(len(lagmuir_others))
