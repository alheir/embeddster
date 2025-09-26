#include "sr595.h"

SR595::SR595(uint8_t dataPin, uint8_t clockPin,
             uint8_t latchPin, uint8_t enablePin,
             uint8_t resetPin, uint8_t numChips)
{
    this->dataPin = dataPin;
    this->clockPin = clockPin;
    this->latchPin = latchPin;
    this->enablePin = enablePin;
    this->resetPin = resetPin;
    this->numChips = numChips;
}

void SR595::begin()
{
    pinMode(this->dataPin, OUTPUT);
    pinMode(this->clockPin, OUTPUT);
    pinMode(this->latchPin, OUTPUT);
    pinMode(this->enablePin, OUTPUT);
    pinMode(this->resetPin, OUTPUT);

    digitalWrite(this->enablePin, HIGH); // Disable output
    digitalWrite(this->resetPin, HIGH); // Not resetting
}

bool SR595::write(const uint8_t *data, size_t length)
{
    if (data == nullptr || length != this->numChips)
    {
        return false;
    }

    digitalWrite(this->latchPin, LOW);
    for (int i = this->numChips - 1; i >= 0; i--)
    {
        shiftOut(this->dataPin, this->clockPin, MSBFIRST, data[i]);
    }
    digitalWrite(this->latchPin, HIGH);

    return true;
}

void SR595::enableOutput(bool enable)
{
    digitalWrite(this->enablePin, enable ? LOW : HIGH);
}

void SR595::reset()
{
    digitalWrite(this->resetPin, LOW);
    delayMicroseconds(10);
    digitalWrite(this->resetPin, HIGH);
}