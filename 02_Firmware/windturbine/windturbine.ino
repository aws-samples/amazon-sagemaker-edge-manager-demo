#include "Adafruit_BME680.h" // version 1.1.1
/// ATTENTION: You need to edit Adafruit_BME680.cpp and comment line 129 --> //_wire->begin();

#include "MPU6050_6Axis_MotionApps_V6_12.h"

#define LIGHT_PIN 2
#define LIGHT_WIND_SPEED_PIN 8
#define VOLTAGE_PIN A0
#define BAUD_RATE 115200
#define BME_CHECK_INTERVAL_MS 10000
#define ROTATION_CHECK_INTERVAL_MS 1000
#define MPU_CHECK_INTERVAL_MS 50

int voltage = 0, errorCode = 0;
uint16_t packetSize;
uint8_t fifoBuffer[64];
char userCommand[] = {' ', '\0'} ;
unsigned long last_bme_check = 0;
unsigned long last_mpu_check = 0;
unsigned long last_rot_check = 0;
float rps = 0; float wind_speed_rps = 0; // rotations per second
int rotation_counter = 0;
int prev_rot_status = 0;
int wind_speed_rotation_counter = 0;
int prev_wind_speed_status = 0;


Quaternion q;
VectorFloat gravity;
VectorInt16 aa;
float currTemp=0;
float temp, humidity, pressure, gas;  // BME readings  

//BME680_Class BME680;  ///< Create an instance of the BME680 class
Adafruit_BME680 bme; // I2C
MPU6050 mpu;

extern char *__brkval;
int freeMemory() {char top; return &top - __brkval;}

void setup() {
  Wire.setClock(200000); // 400kHz I2C clock (200kHz if CPU is 8MHz)
  
  Serial.begin(BAUD_RATE);
  while (Serial.available() && Serial.read()); // empty buffer

  pinMode(VOLTAGE_PIN, INPUT);
  pinMode(LIGHT_PIN, INPUT);
  pinMode(LIGHT_WIND_SPEED_PIN, INPUT);

  if (!bme.begin()) {
    errorCode = 1;
    return;
  }

  mpu.initialize();
  // verify connection
  if (!mpu.testConnection()) {
    // Device communication error
    errorCode = 2;
    return;
  } // if

  // load and configure the DMP
  if (mpu.dmpInitialize() != 0 ) {
    // DMP initialization error
    errorCode = 3;
    return;
  } // if  

  // supply your own gyro offsets here, scaled for min sensitivity
  mpu.setXGyroOffset(-616);
  mpu.setYGyroOffset(-46);
  mpu.setZGyroOffset(5);
  mpu.setXAccelOffset(-1430);
  mpu.setYAccelOffset(-552);
  mpu.setZAccelOffset(1276);
  // Calibration Time: generate offsets and calibrate our MPU6050
  mpu.CalibrateAccel(6);
  mpu.CalibrateGyro(6);
  
  mpu.setDMPEnabled(true);
  
  // get expected DMP packet size for later comparison
  packetSize = mpu.dmpGetFIFOPacketSize();  

//  // Set up oversampling and filter initialization
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150); // 320*C for 150 ms
}

void loop() {
  if (errorCode != 0 ) {
    // keep sending the error signal
    Serial.print("Invalid Intialization. Please fix that and restart. Code: ");
    Serial.println(errorCode);
    delay(3000);
    return;
  } // if

  // read command from host
  if (Serial.available()) {
    int counter = 0;
    while (Serial.available()) {
      char b = Serial.read();
      if ( counter == 0 ) userCommand[0] = b;
      ++counter; // ignore the rest of the characters
    } // while    
  } // if

  bool has_new_data = false;
  if (millis() - last_mpu_check > MPU_CHECK_INTERVAL_MS ) {
    // read a packet from FIFO
    if (mpu.dmpGetCurrentFIFOPacket(fifoBuffer)) {
        // read a packet from FIFO
        mpu.dmpGetQuaternion(&q, fifoBuffer);
        mpu.dmpGetAccel(&aa, fifoBuffer);    
        mpu.dmpGetGravity(&gravity, &q);    
        currTemp = float(mpu.getTemperature())/340.0 + 36.53;
        last_mpu_check = millis();
        has_new_data = true;
    } // if
  } // if
      
  voltage = analogRead(VOLTAGE_PIN);
  int rot_status = digitalRead(LIGHT_PIN);
  int wind_speed_status = digitalRead(LIGHT_WIND_SPEED_PIN);

  if (prev_wind_speed_status != wind_speed_status && wind_speed_status == 0 ) {
    wind_speed_rotation_counter += 1;
  } // if
  prev_wind_speed_status = wind_speed_status;
  
  if (prev_rot_status != rot_status && rot_status == 0 ) {
    rotation_counter += 1;
  } // if
  prev_rot_status = rot_status;
  
  if ( millis() - last_rot_check > ROTATION_CHECK_INTERVAL_MS ) {
    rps = float(rotation_counter) / 16;
    wind_speed_rps = float(wind_speed_rotation_counter) / 16;
    wind_speed_rotation_counter = 0;
    rotation_counter = 0;
    last_rot_check = millis();
    has_new_data = true;
  }

  if (millis() - last_bme_check > BME_CHECK_INTERVAL_MS && bme.remainingReadingMillis() == -1) {
    last_bme_check = millis();
    bme.beginReading();    
  }

  if (bme.remainingReadingMillis() == 0) {
      bme.endReading();
      temp = bme.temperature;
      pressure = bme.pressure / 100.0;
      humidity = bme.humidity;
      gas = bme.gas_resistance / 1000.0;
      has_new_data = true;
  }

  if (!has_new_data) return;
  
  Serial.print(millis()); Serial.print(',');
  Serial.print(freeMemory()); Serial.print(',');

  Serial.print(rps);Serial.print(',');
  Serial.print(wind_speed_rps);Serial.print(',');
  Serial.print(voltage);Serial.print(',');
  Serial.print(q.w); Serial.print(',');
  Serial.print(q.x); Serial.print(',');
  Serial.print(q.y); Serial.print(',');
  Serial.print(q.z); Serial.print(',');
  Serial.print(gravity.x); Serial.print(',');
  Serial.print(gravity.y); Serial.print(',');
  Serial.print(gravity.z); Serial.print(',');
  Serial.print(aa.x); Serial.print(',');
  Serial.print(aa.y); Serial.print(',');
  Serial.print(aa.z); Serial.print(',');
  Serial.print(currTemp); Serial.print(',');  
  Serial.print(temp); Serial.print(',');
  Serial.print(humidity); Serial.print(',');
  Serial.print(pressure); Serial.print(','); 
  Serial.print(gas/100);   
  Serial.print('\n');

}
