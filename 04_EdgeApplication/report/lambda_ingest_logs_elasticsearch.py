# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Set the following env var in your lambda:
# ELASTIC_SEARCH_URL = https://<<YOUR_ELASTICSEARCH_DOMAIN_PREFIX_HERE>>.<<REGION>>.es.amazonaws.com
#
# You need to create these two indices in you Elasticsearch domain (use curl or the Dev Tools console from Kibana to do this):
# PUT wind_turbine_logs
# {
#   "mappings": {
#     "data": {
#       "properties": {
#         "eventTime": {
#           "type": "date",
#           "format": "strict_date_time"
#         },
#         "deviceId": {
#            "type": "keyword"
#         }
#       }
#     }
#   }
# }
# 
# PUT wind_turbine_preds
# {
#  "mappings": {
#     "data": {
#       "properties": {
#         "eventTime": {
#           "type": "date",
#           "format": "strict_date_time"
#         },
#         "deviceId": {
#            "type": "keyword"
#         }
#       }
#     }
#   }
# }
import json
import urllib.request
import os
import io
import boto3
from datetime import datetime

elastic_url = os.getenv("ELASTIC_SEARCH_URL")
s3_client = boto3.client('s3')

# labels we want to use in the Elastic Search payload
log_labels = [
    "rps", "wind_speed_rps", "voltage", "qw", "qx", "qy", "qz",
    "gx", "gy", "gz", "ax", "ay", "az", "gearboxtemp", "ambtemp",
    "humidity", "pressure", "gas"
]

pred_labels= ["roll", "pitch", "yaw", "wind_speed_rps", "rps", "voltage" ]

# add a new record to elastic search
def put_record(record, type):
    base_url = elastic_url
    path = '/wind_turbine_%s/data' % type
    url = base_url + path
    header={'Content-type': 'application/json'}
    try:
        data = json.dumps(record)
        req = urllib.request.Request(url=url, headers=header, method='POST', data=data.encode('utf-8') )
        res = urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(record, type, e)

def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))
    # get the device name and check for the message type: logs or preds
    if event.get('Records') is not None:
        for r in event['Records']:
            bucket = r['s3']['bucket']['name']
            key = r['s3']['object']['key']
            
            with io.BytesIO() as data:
                s3_client.download_fileobj(bucket, key, data)
                data.seek(0)
                log_data = []
                for line in data.readlines():
                    log = json.loads(line)
                    meta = log['eventMetadata']
                    inputs = struct.unpack('6f', base64.b64decode(log['deviceFleetInputs'][0]['data']))
                    outputs = struct.unpack('6f', base64.b64decode(log['deviceFleetOutputs'][0]['data']))
                    item = {
                        "deviceId": meta['deviceId'],
                        "eventTime": "%s+00:00" % datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                    }
                    for i,d in enumerate(pred_labels):
                        item["mean_pred_%s" % d] = str(inputs[i])
                        item["anomaly_%s" % d] = str(outputs[i])
                    put_record(item, 'preds')
    elif event.get('device_name') is not None:
        device_name = event['device_name']
        if event['msg_type'] == 'logs':
            log_data = []
            for logs in event['logs']:
                data = logs['data']
                item = {
                    "deviceId": device_name,
                    "turbineId": device_name.replace('jetson-', 'Turbine '),
                    "arduino_timestamp": data[0],
                    "nanoFreemem": data[1],
                    "eventTime": logs['ts']
                }
                for i,d in enumerate(log_labels):
                    item[d] = data[i+2]
                log_data.append(item)
                put_record(item, 'logs')

            csv_buffer = io.BytesIO()
            csv_buffer.write(json.dumps(log_data).encode('utf-8'))
            csv_buffer.seek(0)
    else:
        raise Exception("Invalid event: %s" % json.dumps(event))
