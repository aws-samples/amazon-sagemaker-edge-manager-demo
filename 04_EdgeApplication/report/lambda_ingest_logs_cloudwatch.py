# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import os
import io
import boto3
import time
import base64
import struct

logs_client = boto3.client('logs')
s3_client = boto3.client('s3')

def put_events(log_stream_name, data):
    resp = logs_client.describe_log_streams(
        logGroupName='/wind-turbine-farm',
        logStreamNamePrefix=log_stream_name
    )
    next_token=resp['logStreams'][0].get('uploadSequenceToken')
    params = dict(
        logGroupName='/wind-turbine-farm',
        logStreamName=log_stream_name,
        logEvents=data
    )
    if next_token is not None:
        params['sequenceToken'] = next_token
    logs_client.put_log_events(**params)
    

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
                    inputs = struct.unpack('6f', base64.b64decode(log['deviceFleetInputs'][0]['data']))
                    outputs = struct.unpack('6f', base64.b64decode(log['deviceFleetOutputs'][0]['data']))
                    log_data.append({
                        'timestamp': round(time.time() * 1000),
                        'message': ' '.join([str(i) for i in (inputs + outputs)])
                    })
            put_events('preds', log_data)
    elif event.get('device_name') is not None:
        device_name = event['device_name']
        if event['msg_type'] == 'logs':
            log_data = []
            for logs in event['logs']:
                data = logs['data']
                log_data.append({
                    'timestamp': round(time.time() * 1000),
                    'message': ' '.join([logs['ts'], device_name] + [str(i) for i in data])
                })
            put_events('sensors', log_data)
    else:
        raise Exception("Invalid event: %s" % json.dumps(event))
   
