# AWS Lambda functions for ingesting data into your report tool

If you want to visualize the anomalies and the logs, you can use one these lambda functions to ingest data into Elasticsearch or CloudWatch Logs.

The lambdas need to be 'configured' to capture 'Put' events in the S3 bucket, used by SageMaker Edge Agent to store data (CaptureData). For each Json lines file stored in this bucket the Lambda function will parse it and send the data to the chosen report tool. Also, for the application logs, sent by the application to an MQTT topic, you need to configure an IoT Rule that will capture the data (with the following query) and invoke the same Lambda function:
```sql
SELECT 'logs' as msg_type, topic(3) as device_name, * FROM 'wind-turbine/logs/#' 
```

## Elasticsearch + Kibana
You need to create two indices in your Elasticsearch first. In the Kibana console, go to 'Dev Tools', copy and paste the following content and run:
```html
PUT wind_turbine_logs
{
  "mappings": {
    "data": {
      "properties": {
        "eventTime": {
          "type": "date",
          "format": "strict_date_time"
        },
        "deviceId": {
           "type": "keyword"
        }
      }
    }
  }
}

PUT wind_turbine_preds
{
 "mappings": {
    "data": {
      "properties": {
        "eventTime": {
          "type": "date",
          "format": "strict_date_time"
        },
        "deviceId": {
           "type": "keyword"
        }
      }
    }
  }
}
```
This [Lambda](/04_EdgeApplication/setup/lambda_ingest_logs_elasticsearch.py) requires an environment variable, that needs to be defined in the AWS Lambda console, while you're creating this function:
```bash
ELASTIC_SEARCH_URL = https://<<YOUR_ELASTICSEARCH_DOMAIN_PREFIX_HERE>>.<<REGION>>.es.amazonaws.com
```

<table>
  <tr>
    <td><img width="500px" src="/imgs/KibanaAnomalies.png"</img></td>
    <td><img width="500px" src="/imgs/KibanaAnomaliesOverTime.png"</img></td>
  </tr>
</table>

## CloudWatch
This [Lambda](/04_EdgeApplication/setup/lambda_ingest_logs_cloudwatch.py) requires that you first create, in your AWS CloudWatch Logs console, a log group named **/wind-turbine-farm**. Then, inside this log group, create two **log streams**: preds and sensors.

Now, after start ingesting data to these log streams, you can create queries and dashboards. Some examples of queries:

### Rotation Avg
```sql
parse '* * * * * * * * * * * * * * * * * * * * * *' as
  ts, device_name, arduino_timestamp, arduino_freemem, rps, wind_speed_rps,
    voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp,
    air_humidity, air_pressure, air_quality
    | filter @logStream like /sensors/
    | sort @timestamp desc
    | limit 20
    | stats avg(rps) as rps_avg,
            avg(wind_speed_rps) as wind_speed_rps_avg
            by bin(1m)
```
### Voltage Avg
```sql
parse '* * * * * * * * * * * * * * * * * * * * * *' as
  ts, device_name, arduino_timestamp, arduino_freemem, rps, wind_speed_rps,
    voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp,
    air_humidity, air_pressure, air_quality
    | filter @logStream like /sensors/
    | sort @timestamp desc
    | limit 20
    | stats avg(voltage) as voltage_avg
            by bin(1m)
```
### Vibration Avg
```sql
parse '* * * * * * * * * * * * * * * * * * * * * *' as
  ts, device_name, arduino_timestamp, arduino_freemem, rps, wind_speed_rps,
    voltage, qw, qx, qy, qz, gx, gy, gz, aax,aay,aaz, gearbox_temp, ambient_temp,
    air_humidity, air_pressure, air_quality
    | filter @logStream like /sensors/
    | sort @timestamp desc
    | limit 20
    | stats avg(qw) as qw_avg,
            sum(qx) as qx_avg,
            avg(qy) as qy_avg,
            avg(qz) as qz_avg
            by bin(1m)
```
### Anomalies Count
```sql
parse '* * * * * * * * * * * *' as 
  roll_mae, pitch_mae, yaw_mae, wind_mae, rps_mae, voltage_mae, 
  roll_anom, pitch_anom, yaw_anom, wind_anom, rps_anom, voltage_anom
| filter @logStream like /preds/
| sort @timestamp desc
| limit 20
| stats sum(roll_anom) as roll_anomalies, 
        sum(pitch_anom) as pitch_anomalies,
        sum(yaw_anom) as yaw_anomalies,
        sum(wind_anom) as wind_anomalies,
        sum(rps_anom) as rps_anomalies,
        sum(voltage_anom) as voltage_anomalies
        by bin(1m)
| sort maxBytes desc
```

<table>
  <tr>
    <td><img width="600px" src="/imgs/CloudWatchAppData.png"</img></td>
  </tr>
</table>



