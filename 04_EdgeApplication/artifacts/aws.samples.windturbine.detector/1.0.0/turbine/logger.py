# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import threading
import json
import logging
import turbine.util as util
import turbine.ggv2_client as ggv2_client
import traceback

logger = logging.getLogger(__name__)

class Logger(object):    
    def __init__(self, device_name):
        '''
            This class is responsible for sending application logs
            to the cloud via MQTT and IoT Topics
        '''
        self.device_name = device_name
        logger.info("Device Name: %s" % self.device_name)
        self.ggv2_client = ggv2_client

        self.logs_buffer = []
        self.__log_lock = threading.Lock()

    def __run_logs_upload_job__(self):        
        '''
            Launch a thread that will read the logs buffer
            prepare a json document and send the logs
        '''
        self.cloud_log_sync_job = threading.Thread(target=self.__upload_logs__)
        self.cloud_log_sync_job.start()
        
    def __upload_logs__(self):
        '''
            Invoked by the thread to publish the latest logs
        '''
        self.__log_lock.acquire(True)
        f = json.dumps({'logs': self.logs_buffer})
        self.logs_buffer = [] # clean the buffer
        try:
            self.ggv2_client.publish( topic='wind-turbine/logs/%s' % self.device_name, message=f.encode("utf8"), qos=ggv2_client.QOS.AT_LEAST_ONCE )
        except Exception as e:
            traceback.print_exc()
            logger.error(e)
            
        logger.info("New log file uploaded. len: %d" % len(f))
        self.__log_lock.release()
 
    def publish_logs(self, data):
        '''
            Invoked by the application, it buffers the logs            
        '''
        buffer_len = 0
        if self.__log_lock.acquire(False):
            self.logs_buffer.append(data)
            buffer_len = len(self.logs_buffer)
            self.__log_lock.release()
        # else: job is running, discard the new data
        if buffer_len > 10:
            # run the sync job
            self.__run_logs_upload_job__()
