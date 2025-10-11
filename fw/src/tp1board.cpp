#include "tp1board.h"
#include "sr595.h"

#define TP1BOARD_NUMSR595S 2

// Segment patterns: A B C D E F G DP (bit 7 = DP, 6=G, ..., 0=A)
// for common anode display
const uint8_t TP1BOARD::segmentPatterns[16] = {
    0b11000000, // 0
    0b11111001, // 1
    0b10100100, // 2
    0b10110000, // 3
    0b10011001, // 4
    0b10010010, // 5
    0b10000010, // 6
    0b11111000, // 7
    0b10000000, // 8
    0b10010000, // 9
    0b10001000, // A
    0b10000011, // b
    0b11000110, // C
    0b10100001, // d
    0b10000110, // E
    0b10001110  // F
};

TP1BOARD::TP1BOARD() : sr(PIN_595_SI, PIN_595_SHIFT_CLK,
                          PIN_595_LATCH_CLK, PIN_595_nOE,
                          PIN_595_nRST, TP1BOARD_NUMSR595S),
                       currentDigit(0), lastRefresh(0)
{
    memset(digits, 0, sizeof(digits));
    ledStates = 0;
}

void TP1BOARD::begin()
{
    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    pinMode(PIN_ENC_SW, INPUT_PULLUP);

    sr.begin();
    sr.reset(true);
    sr.enableOutput(true);
}

void TP1BOARD::setDigit(uint8_t digit, char c)
{
    if (digit < 4)
    {
        digits[digit] = charToSegments(c);
    }
}

void TP1BOARD::setLED(uint8_t led, bool on)
{
    // LEDs:
    // 0: Status 0 (mux control bit 0)
    // 1: Status 1 (mux control bit 1)
    // 2: White (D3)
    // 3: Yellow (D4)
    // 4: Blue (D5)
    // 5: Green (D6)
    uint16_t bit = 0;
    if (led == 0)
        bit = STATUS_0_BIT;
    else if (led == 1)
        bit = STATUS_1_BIT;
    else if (led == 2)
        bit = LED_D3_W_BIT;
    else if (led == 3)
        bit = LED_D4_Y_BIT;
    else if (led == 4)
        bit = LED_D5_B_BIT;
    else if (led == 5)
        bit = LED_D6_G_BIT;

    if (bit != 0)
    {
        if (on)
        {
            ledStates |= bit;
        }
        else
        {
            ledStates &= ~bit;
        }
    }
}

void TP1BOARD::refresh()
{
    uint32_t now = millis();
    if (now - lastRefresh < TP1BOARD_REFRESH_MS)
        return;
    lastRefresh = now;

    // MSB first: chip1 then chip0)
    uint8_t data[2] = {0, 0};

    uint16_t selectors = 0;
    if (currentDigit & 0x01)
        selectors |= SEL_0_BIT;
    if (currentDigit & 0x02)
        selectors |= SEL_1_BIT;

    uint16_t fullData = digits[currentDigit] | selectors | ledStates;
    data[0] = fullData & 0xFF;        // Lower 8 bits
    data[1] = (fullData >> 8) & 0xFF; // Upper 8 bits

    sr.write(data, 2);

    currentDigit = (currentDigit + 1) % 4;
}

int8_t TP1BOARD::getEncoderDelta()
{
    static uint8_t lastState = 0;
    uint8_t a = digitalRead(PIN_ENC_A);
    uint8_t b = digitalRead(PIN_ENC_B);
    uint8_t state = (a << 1) | b;

    int8_t delta = 0;
    if (lastState == 0b00 && state == 0b01)
        delta = 1;
    else if (lastState == 0b01 && state == 0b11)
        delta = 1;
    else if (lastState == 0b11 && state == 0b10)
        delta = 1;
    else if (lastState == 0b10 && state == 0b00)
        delta = 1;
    else if (lastState == 0b00 && state == 0b10)
        delta = -1;
    else if (lastState == 0b10 && state == 0b11)
        delta = -1;
    else if (lastState == 0b11 && state == 0b01)
        delta = -1;
    else if (lastState == 0b01 && state == 0b00)
        delta = -1;

    lastState = state;
    return delta;
}

bool TP1BOARD::getEncoderButton()
{
    return digitalRead(PIN_ENC_SW) == ENC_SW_ACTIVE;
}

uint8_t TP1BOARD::charToSegments(char c)
{
    if (c >= '0' && c <= '9')
        return segmentPatterns[c - '0'];
    if (c >= 'A' && c <= 'F')
        return segmentPatterns[10 + (c - 'A')];
    if (c >= 'a' && c <= 'f')
        return segmentPatterns[10 + (c - 'a')];

    return 0;
}

void TP1BOARD::setStatusLED(uint8_t index, bool on)
{
    if (index < 2) // Only 0 and 1
    {
        setLED(index, on);
    }
}

void TP1BOARD::setMuxLED(uint8_t selection)
{
    // Mux control: STATUS_1 STATUS_0 -> LED
    // 00 -> none
    // 01 -> D1
    // 10 -> D2
    // 11 -> D3
    uint16_t mask = STATUS_0_BIT | STATUS_1_BIT;
    uint16_t bits = 0;
    if (selection == 1) bits = STATUS_0_BIT;          // 01
    else if (selection == 2) bits = STATUS_1_BIT;     // 10
    else if (selection == 3) bits = STATUS_0_BIT | STATUS_1_BIT; // 11
    // else 0 for none or invalid

    ledStates = (ledStates & ~mask) | bits;
}

void TP1BOARD::setColorLED(uint8_t color, bool on)
{
    if (color < 4) // 0=White, 1=Yellow, 2=Blue, 3=Green
    {
        setLED(color + 2, on); // LEDs 2-5
    }
}

void TP1BOARD::setColorLEDs(bool white, bool yellow, bool blue, bool green)
{
    setColorLED(0, white);
    setColorLED(1, yellow);
    setColorLED(2, blue);
    setColorLED(3, green);
}
