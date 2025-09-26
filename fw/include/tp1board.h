#ifndef TP1BOARD_H
#define TP1BOARD_H

#include <Arduino.h>
#include "pin_assignment.h"
#include "sr595.h"

#define TP1BOARD_NDIGITS 4
#define TP1BOARD_NLEDS 6
#define TP1BOARD_REFRESH_MS 5 // Multiplex refresh interval

class TP1BOARD
{
public:
    TP1BOARD();
    void begin();

    void setDigit(uint8_t digit, char c);

    void setLED(uint8_t led, bool on);

    // refresh the multiplexed display; call periodically in loop())
    void refresh();

    // returns delta (-1, 0, +1) for rotation
    int8_t getEncoderDelta();
    bool getEncoderButton();

private:
    SR595 sr;
    uint8_t digits[TP1BOARD_NDIGITS];
    uint16_t ledStates;
    uint8_t currentDigit;
    uint32_t lastRefresh;

    static const uint8_t segmentPatterns[16];

    uint8_t charToSegments(char c);
};

#endif // TP1BOARD_H