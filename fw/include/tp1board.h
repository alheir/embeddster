#ifndef TP1BOARD_H
#define TP1BOARD_H

#include <Arduino.h>
#include "pin_assignment.h"
#include "sr595.h"

#define TP1BOARD_NDIGITS 4
#define TP1BOARD_NLEDS 6
#define TP1BOARD_REFRESH_MS 10 // Multiplex refresh interval

// LED indices for easier reference
enum LedIndex {
    LED_STATUS_0 = 0,
    LED_STATUS_1 = 1,
    LED_WHITE = 2,
    LED_YELLOW = 3,
    LED_BLUE = 4,
    LED_GREEN = 5
};

class TP1BOARD
{
public:
    TP1BOARD();
    void begin();

    void setDigit(uint8_t digit, char c);

    // Set LED by index (0-5): 0=Status0 bit, 1=Status1 bit, 2=White, 3=Yellow, 4=Blue, 5=Green
    void setLED(uint8_t led, bool on);

    // Helper method for mux-controlled LEDs: 0=none, 1=D1, 2=D2, 3=D3
    void setMuxLED(uint8_t selection);

    // Helper methods for status LEDs (controlled by mux, indices 0-1)
    void setStatusLED(uint8_t index, bool on);

    // Helper methods for color LEDs (4 colors: 0=White, 1=Yellow, 2=Blue, 3=Green)
    void setColorLED(uint8_t color, bool on);
    void setColorLEDs(bool white, bool yellow, bool blue, bool green);

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