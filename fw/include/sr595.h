#ifndef SR595_H
#define SR595_H

#include <Arduino.h>

class SR595
{
public:
    SR595(uint8_t dataPin, uint8_t clockPin,
          uint8_t latchPin, uint8_t enablePin,
          uint8_t resetPin, uint8_t numChips);
          
    void begin();
    bool write(const uint8_t* data, size_t length);

    // controls outputs to high impedance; disabled by default
    void enableOutput(bool enable); 

    // resets the shift registers
    void reset(bool latchAfter = false); 

private:
    uint8_t dataPin;
    uint8_t clockPin;
    uint8_t latchPin;
    uint8_t enablePin;
    uint8_t resetPin;
    uint8_t numChips;
};

#endif // SR595_H
