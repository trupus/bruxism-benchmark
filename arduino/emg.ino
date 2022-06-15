// All definitions
#define NUMCHANNELS 4
#define SAMPFREQ 256                      // ADC sampling rate 256
#define PERIOD_us (1000000/(SAMPFREQ))    // Set 256Hz sampling frequency       

// Global constants and variables
unsigned char CurrentCh;         //Current channel being sampled.
unsigned long last_us = 0L;      // Helper for the sample rate

//~~~~~~~~~~
// Functions
//~~~~~~~~~~

/****************************************************/
/*  Function name: setup                            */
/*  Parameters                                      */
/*    Input   :  No	                                */
/*    Output  :  No                                 */
/*    Action  : Initializes all peripherals         */
/****************************************************/
void setup() {
 // Serial Port
 Serial.begin(115200);
}


/****************************************************/
/*  Function name: loop                             */
/*  Parameters                                      */
/*    Input   :  No	                                */
/*    Output  :  No                                 */
/*    Action  :  Reads the data.                    */
/****************************************************/
void loop() {
  if (micros() - last_us > PERIOD_us) {
    last_us += PERIOD_us;

    //Read the 4 ADC inputs
    for(CurrentCh = 0; CurrentCh < NUMCHANNELS; CurrentCh++){
        Serial.print(analogRead(CurrentCh)); 

      if (CurrentCh != NUMCHANNELS - 1) {
        Serial.print(","); 
      }
    }
    Serial.println();
  }
}