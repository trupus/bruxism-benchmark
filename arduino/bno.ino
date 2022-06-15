#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

//                                   id, address
Adafruit_BNO055 bno0 = Adafruit_BNO055(-1, 0x28);
Adafruit_BNO055 bno1 = Adafruit_BNO055(-1, 0x29);

adafruit_bno055_offsets_t bno_offset28 = { -39, -18, -39, 123, 211, -400, -1, -1, 0, 1000, 747 };
adafruit_bno055_offsets_t bno_offset29 = { -12, -28, -46, 25, 437, -66, -2, 1, 0, 1000, 718 };

sensors_event_t orientationData[2], angVelocityData[2], linearAccelData[2], magnetometerData[2], accelerometerData[2], gravityData[2];
imu::Quaternion quat[2];

void setup(void)
{
  Serial.begin(500000);

  /* Initialise the sensor */
  setupBNO(&bno0, &bno_offset28);
  setupBNO(&bno1, &bno_offset29);
}

void loop(void)
{
  readData(&bno0, 0);
  readData(&bno1, 1);

  printData(0);
  Serial.print(",");
  printData(1);

  Serial.println();
}

void setupBNO(Adafruit_BNO055* bno, adafruit_bno055_offsets_t* offsets) {
  if (!bno->begin())
  {
    /* There was a problem detecting the BNO055 ... check your connections */
    Serial.print("Ooops, no BNO055 detected ... Check your wiring or I2C ADDR!");
    while (1);
  }
  delay(1000);
  
  bno->setSensorOffsets(*offsets);
  delay(1000);

  bno->setExtCrystalUse(true);
}

void readData(Adafruit_BNO055* bno, byte index) {
//  bno->getEvent(&orientationData[index], Adafruit_BNO055::VECTOR_EULER);
  bno->getEvent(&angVelocityData[index], Adafruit_BNO055::VECTOR_GYROSCOPE);
//  bno->getEvent(&linearAccelData[index], Adafruit_BNO055::VECTOR_LINEARACCEL);
//  bno->getEvent(&magnetometerData[index], Adafruit_BNO055::VECTOR_MAGNETOMETER);
  bno->getEvent(&accelerometerData[index], Adafruit_BNO055::VECTOR_ACCELEROMETER);
//  bno->getEvent(&gravityData[index], Adafruit_BNO055::VECTOR_GRAVITY);
  quat[index] = bno->getQuat();
}

void printData(byte index) {
//  printEvent(&orientationData[index]);
  printEvent(&angVelocityData[index]);
//  printEvent(&linearAccelData[index]);
//  printEvent(&magnetometerData[index]);
  printEvent(&accelerometerData[index]);
//  printEvent(&gravityData[index]);

  Serial.print(quat[index].w());
  Serial.print(",");
  Serial.print(quat[index].x());
  Serial.print(",");
  Serial.print(quat[index].y());
  Serial.print(",");
  Serial.print(quat[index].z());
}

void printEvent(sensors_event_t* event) {
  double x = -1000000, y = -1000000 , z = -1000000; //dumb values, easy to spot problem
  if (event->type == SENSOR_TYPE_ACCELEROMETER) {
    x = event->acceleration.x;
    y = event->acceleration.y;
    z = event->acceleration.z;
  }
  else if (event->type == SENSOR_TYPE_ORIENTATION) {
    x = event->orientation.x;
    y = event->orientation.y;
    z = event->orientation.z;
  }
  else if (event->type == SENSOR_TYPE_MAGNETIC_FIELD) {
    x = event->magnetic.x;
    y = event->magnetic.y;
    z = event->magnetic.z;
  }
  else if (event->type == SENSOR_TYPE_GYROSCOPE) {
    x = event->gyro.x;
    y = event->gyro.y;
    z = event->gyro.z;
  }
  else if (event->type == SENSOR_TYPE_ROTATION_VECTOR) {
    x = event->gyro.x;
    y = event->gyro.y;
    z = event->gyro.z;
  }
  else if (event->type == SENSOR_TYPE_LINEAR_ACCELERATION) {
    x = event->acceleration.x;
    y = event->acceleration.y;
    z = event->acceleration.z;
  }
  else if (event->type == SENSOR_TYPE_GRAVITY) {
    x = event->acceleration.x;
    y = event->acceleration.y;
    z = event->acceleration.z;
  }

  Serial.print(x);
  Serial.print(",");
  Serial.print(y);
  Serial.print(",");
  Serial.print(z);
  Serial.print(",");
}