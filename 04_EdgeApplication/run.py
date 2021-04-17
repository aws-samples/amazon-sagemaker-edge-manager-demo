#!/usr/bin/python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import numpy as np
import io
import serial
import json
import logging
import argparse
import time
import requests
import gzip

import turbine

from datetime import datetime

if __name__ == '__main__':
    # parse the input parameters    
    parser = argparse.ArgumentParser()

    parser.add_argument('--test-mode', action="store_true", help="Use a dummy file as sensors readings")
    parser.add_argument('--inject-noise', action="store_true", help="Add random noise to the raw data")
    parser.add_argument("--debug", action="store_true", help='Enable debugging messages')    

    parser.add_argument('--agent-socket', type=str, default="/tmp/edge_agent", help='The unix socket path created by the agent')
    parser.add_argument('--model-path', type=str, default=os.path.join(os.environ["SM_EDGE_AGENT_HOME"], 'models'), help='Absolute path to the model dir')

    parser.add_argument('--serial-port', type=str, default="/dev/ttyUSB0", help='Path to the USB port used by the wind turbine')
    parser.add_argument('--serial-baud', type=int, default=115200, help='Serial comm. speed in bits per second')

    parser.add_argument('--sagemaker-edge-configfile-path', type=str, default=os.path.join(os.environ["SM_EDGE_AGENT_HOME"], "sagemaker_edge_config.json"), help='Path to the agent config file')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO )
    logging.debug("Parsing parameters")

    # load sagemaker edge agent config file
    iot_params = json.loads(open(args.sagemaker_edge_configfile_path, 'r').read())

    # retrieve the IoT thing name associated with the edge device
    iot_client = turbine.get_client('iot', iot_params)
    sm_client = turbine.get_client('sagemaker', iot_params)
    resp = sm_client.describe_device(
        DeviceName=iot_params['sagemaker_edge_core_device_uuid'], 
        DeviceFleetName=iot_params['sagemaker_edge_core_device_fleet_name']
    )    
    device_name = resp['IotThingName']
    mqtt_host=iot_client.describe_endpoint(endpointType='iot:Data-ATS')['endpointAddress']
    mqtt_port=8883

    # buffer size required to process timeseries data
    PREDICTIONS_INTERVAL = 1.0 # interval in seconds between the predictions
    MIN_NUM_SAMPLES = 500         
    INTERVAL = 5 # seconds
    TIME_STEPS = 20 * INTERVAL
    STEP = 10
    FEATURES_IDX = [6,7,8,5,  3, 2, 4] # qX,qy,qz,qw  ,wind_seed_rps, rps, voltage 
    NUM_RAW_FEATURES = 20
    NUM_FEATURES = 6

    # Some constants used for data prep + compare the results
    thresholds = np.load('statistics/thresholds.npy')
    raw_std = np.load('statistics/raw_std.npy')
    mean = np.load('statistics/mean.npy')
    std = np.load('statistics/std.npy')

    logging.info("Initializing...")
    # Sends the logs to the cloud via MQTT Topics
    logger = turbine.Logger(device_name, iot_params)

    # Initialize the Edge Manager agent
    edge_agent = turbine.EdgeAgentClient(args.agent_socket)
    
    model_loaded = False
    model_name = None
    def model_update_callback(name, version):
        global model_loaded, model_name
        model_version=str(version)
        model_name = "%s-%s" % (name, model_version.replace('.', '-')) 
        logging.info('New model deployed: %s - %s - %s' % (name, model_version, model_name))
        resp = edge_agent.load_model(model_name, os.path.join(args.model_path, name, model_version))
        if resp is None: 
            logging.error('It was not possible to load the model. Is the agent running?')
            return
        model_loaded = True 

    ## Initialize the OTA Model Manager
    model_manager = turbine.OTAModelUpdate(device_name, iot_params, mqtt_host, mqtt_port, model_update_callback, args.model_path)
   
    ## Initialize sensors reader
    if args.test_mode:
        logging.info('Using Dummy sensors readings')
        # use a local file to simulate the raw data collected from the turbine's sensors
        if not os.path.exists('dataset_wind.csv'):
            req = requests.get('https://aws-ml-blog.s3.amazonaws.com/artifacts/monitor-manage-anomaly-detection-model-wind-turbine-fleet-sagemaker-neo/dataset_wind_turbine.csv.gz')
            with gzip.GzipFile(fileobj=io.BytesIO(req.content), mode="r:gz") as f:
                with open('dataset_wind.csv', 'w') as d: d.write(f.read().decode('utf-8'))

        class DummySensors(object):
            def __init__(self):
                self.buffer = open('dataset_wind.csv', 'r').readlines()[1:] # skip the file header
                self.idx = 0
            def isOpen(self): return True
            def close(self): pass
            def readline(self):
                if self.idx >= len(self.buffer): self.idx = 0
                reading = self.buffer[self.idx].strip().split(',')[2:] # drop the first two columns
                reading = reading[0:2] + [reading[3], reading[-1]] + reading[4:-1] # reorganize the columns
                reading = ",".join(reading).encode('utf-8')
                self.idx += 1
                return reading

        turbine_sensors = DummySensors()
    else:
        logging.info('Reading from the sensors of the turbine')
        # Initialize the turbine program
        turbine_sensors = serial.Serial(port=args.serial_port, baudrate=args.serial_baud)

    logging.info("Defining parameters")

    # main loop
    samples = []
    logging.info("Starting main loop..")
    try:
        while turbine_sensors.isOpen(): # runs while it communicates with the arduino
            if not model_loaded:
                logging.info("Waiting for the model...")
                time.sleep(5)
                continue

            # get the (raw) sensors data
            data = ""
            try:
                data = turbine_sensors.readline().decode('utf-8').strip()
                tokens = np.array(data.split(','))

                # check if the format is correct
                if len(tokens) != NUM_RAW_FEATURES:
                    print(data)
                    logging.error('Wrong # of features. Expected: %d, Got: %d' % ( NUM_RAW_FEATURES, len(tokens)))
                    time.sleep(1)
                    continue
                if args.inject_noise:
                    if np.random.randint(50) == 0:
                        tokens[FEATURES_IDX[0:4]] = np.random.rand(4) * 10 # out of the radians range
                    if np.random.randint(20) == 0:
                        tokens[FEATURES_IDX[5]] = np.random.rand(1)[0] * 10 # out of the normalized wind range
                    if np.random.randint(50) == 0:
                        tokens[FEATURES_IDX[6]] = int(np.random.rand(1)[0] * 1000) # out of the normalized voltage range
                # get only the used features
                data = [float(tokens[i]) for i in FEATURES_IDX]
            except Exception as e:
                logging.error(e)
                logging.error(data)
                continue


            # compute the euler angles from the quaternion
            roll,pitch,yaw = turbine.euler_from_quaternion(data[0],data[1],data[2],data[3])
            data = np.array([roll,pitch,yaw, data[4], data[5], data[6]])
            samples.append(data)
            
            ts = "%s+00:00" % datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            # Log the reading
            logger.publish_logs({'ts': ts, 'data': tokens.tolist()})

            if len(samples) <= MIN_NUM_SAMPLES:
                if len(samples) % 10 == 0:
                    logging.info('Buffering %d/%d... please wait' % (len(samples), MIN_NUM_SAMPLES))
                # buffering
                continue

            # prep the data for the model
            data = np.array(samples) # create a copy
            samples = samples[1:] # remove the oldest sample            
            data = np.array([turbine.wavelet_denoise(data[:,i], raw_std[i], 'db6') for i in range(NUM_FEATURES)])

            data = data.transpose((1,0))
            data -= mean
            data /= std
            data = data[-(TIME_STEPS+STEP):]

            x = turbine.create_dataset(data, TIME_STEPS, STEP)
            x = np.transpose(x, (0, 2, 1)).reshape(x.shape[0], NUM_FEATURES, 10, 10)
            # invoke the model
            p = edge_agent.predict(model_name, x)
            a = x.reshape(x.shape[0], NUM_FEATURES, 100).transpose((0,2,1))
            b = p.reshape(p.shape[0], NUM_FEATURES, 100).transpose((0,2,1))

            # check the anomalies
            pred_mae_loss = np.mean(np.abs(b - a), axis=1).transpose((1,0))
            values = np.mean(pred_mae_loss, axis=1)
            anomalies = (values > thresholds)
            # capture some metrics
            edge_agent.capture_data(model_name, values.astype(np.float32), anomalies.astype(np.float32))

            if anomalies.any():
                logging.info("Anomaly detected: %s" % anomalies)
            else:
                logging.info("Ok")

            time.sleep(PREDICTIONS_INTERVAL)
    except KeyboardInterrupt as e:
        pass
    except Exception as e:
        logging.error(e)
     
    logging.info("Shutting down")
    if model_loaded: edge_agent.unload_model(model_name)
    del model_manager
    del edge_agent
    del logger
    turbine_sensors.close()
