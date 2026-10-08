#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

SparkFun_VL53L5CX myImager;
VL53L5CX_ResultsData measurementData; 

const int pirPin = 13;

void setup() {
  Serial.begin(115200);
  delay(1000); 

  pinMode(pirPin, INPUT);
  
  Wire.begin();
  if (myImager.begin() == false) {
    while (1) ; 
  }
  
  myImager.setResolution(8 * 8);
  myImager.startRanging();
}

void loop() {
  if (myImager.isDataReady() == true) {
    myImager.getRangingData(&measurementData);

    for (int i = 0; i < 64; i++) {
      Serial.print(measurementData.distance_mm[i]);
      Serial.print(",");
    }
    // Print the PIR state and end the line
    Serial.println(digitalRead(pirPin));
  }
}