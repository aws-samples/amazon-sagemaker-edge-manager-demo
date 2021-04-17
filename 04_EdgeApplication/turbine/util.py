# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import math
import numpy as np
import boto3
import pywt
import socket
import requests
import json

def euler_from_quaternion(x, y, z, w):
    """
    Convert a quaternion into euler angles (roll, pitch, yaw)
    roll is rotation around x in radians (counterclockwise)
    pitch is rotation around y in radians (counterclockwise)
    yaw is rotation around z in radians (counterclockwise)
    """
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll_x = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch_y = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)

    return roll_x, pitch_y, yaw_z # in radians

def wavelet_denoise(data, noise_sigma, wavelet):
    '''Filter accelerometer data using wavelet denoising    
    Modification of F. Blanco-Silva's code at: https://goo.gl/gOQwy5
    '''
    wavelet = pywt.Wavelet(wavelet)
    levels  = min(5, (np.floor(np.log2(data.shape[0]))).astype(int))
    # Francisco's code used wavedec2 for image data
    wavelet_coeffs = pywt.wavedec(data, wavelet, level=levels)
    threshold = noise_sigma*np.sqrt(2*np.log2(data.size))

    new_wavelet_coeffs = map(lambda x: pywt.threshold(x, threshold, mode='soft'), wavelet_coeffs)

    return pywt.waverec(list(new_wavelet_coeffs), wavelet)

def create_dataset(X, time_steps=1, step=1):
    '''
        Format a timeseries buffer into a multidimensional tensor
        required by the model
    '''
    Xs = []
    for i in range(0, len(X) - time_steps, step):
        v = X[i:(i + time_steps)]
        Xs.append(v)
    return np.array(Xs)

def get_aws_credentials(cred_endpoint, thing_name, cert_file, key_file, ca_file):
    '''
        Invoke SageMaker Edge Manager endpoint to exchange the certificates
        by temp credentials
    '''
    resp = requests.get(
        cred_endpoint,
        cert=(cert_file, key_file, ca_file),
    )
    if not resp:
        raise Exception('Error while getting the IoT credentials: ', resp)
    credentials = resp.json()
    return (credentials['credentials']['accessKeyId'],
        credentials['credentials']['secretAccessKey'],
        credentials['credentials']['sessionToken'])

def get_client(service_name, iot_params):
    '''
        Build a boto3 client of a given service
        It uses the temp credentials exchanged by the certificates
    '''
    access_key_id,secret_access_key,session_token = get_aws_credentials(
        iot_params['sagemaker_edge_provider_aws_iot_cred_endpoint'],
        iot_params['sagemaker_edge_core_device_uuid'],
        iot_params['sagemaker_edge_provider_aws_cert_file'],
        iot_params['sagemaker_edge_provider_aws_cert_pk_file'],
        iot_params['sagemaker_edge_provider_aws_ca_cert_file']
    )
    return boto3.client(
        service_name, iot_params['sagemaker_edge_core_region'],
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        aws_session_token=session_token
    )

