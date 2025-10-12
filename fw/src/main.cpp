#include <Arduino.h>
#include "pin_assignment.h"

// ============================================================================
// CONFIGURACIÓN Y DEFINICIONES
// ============================================================================

#define BAUD_RATE 115200
#define SETUP_DELAY_MS 250

// NeoPixel
#include <Adafruit_NeoPixel.h>
#define NUMPIXELS 1
#define NPXL_BRIGHTNESS 15
Adafruit_NeoPixel npxl(NUMPIXELS, PIN_NPXL, NEO_GRB + NEO_KHZ800);

// MCP CAN
#include <mcp_can.h>
#include <SPI.h>
MCP_CAN CAN(PIN_MCP_nCS);

// TP1 Board
#include "tp1board.h"
TP1BOARD board;

// ============================================================================
// ENUMS Y ESTRUCTURAS
// ============================================================================

enum State
{
    STATE_SNIFFER,
    STATE_RANDOM_SEND,
    STATE_N
};

// ============================================================================
// VARIABLES GLOBALES
// ============================================================================

// Estados
uint8_t currState = STATE_SNIFFER;
uint8_t nextState = STATE_RANDOM_SEND;

// Retry mechanism
#define RETRY_INTERVAL_MS 2000
bool retryMode = false;
uint32_t lastRetryAttempt = 0;
char retryBuffer[8];
int retryLen = 0;
long retryId = 0;

// Node configuration
#define GROUP_NUMBER 0
#define NODE_ID (0x100 + GROUP_NUMBER)

// Random send configuration
#define NUM_RANDOM_STATIONS 4
#define MIN_DELAY_BETWEEN_SEND_MS 100
#define MAX_DELAY_BETWEEN_SEND_MS 2000
#define MAX_DELTA_ANGLE 30

// ============================================================================
// DECLARACIÓN DE FUNCIONES
// ============================================================================

void do_can_sniffer();
void do_can_random_send();
void enterRetryMode(long canId, const char *data, int len);
void exitRetryMode(bool success);

// ============================================================================
// SETUP
// ============================================================================

void setup()
{
    Serial.begin(BAUD_RATE);
    Serial.println("\n\n~~~~CAN SNIFFER/RANDOM SENDER~~~~\n");
    Serial.println("Serial init ok");

    delay(SETUP_DELAY_MS);
    Serial.println("\n~~~~\n");

    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Onboard LED init ok");

    delay(SETUP_DELAY_MS);
    Serial.println("\n~~~~\n");

    if (!npxl.begin())
    {
        Serial.println("NEOPIXEL init fail");
        while (1)
            ;
    }
    Serial.println("NEOPIXEL init ok");
    npxl.setPixelColor(0, npxl.Color(0, 0, 0));
    npxl.show();

    delay(SETUP_DELAY_MS);
    Serial.println("\n~~~~\n");

    board.begin();
    for (int i = 0; i < 3; i++)
    {
        board.setColorLEDs(true, true, true, true);
        board.refresh();
        delay(50);
        board.setColorLEDs(false, false, false, false);
        board.refresh();
        delay(50);
    }
    Serial.println("TP1BOARD init ok");

    delay(SETUP_DELAY_MS);
    Serial.println("\n~~~~\n");

    pinMode(PIN_MCP_nINT, INPUT);
    if (CAN.begin(MCP_ANY, CAN_125KBPS, MCP_16MHZ) == CAN_FAILINIT)
    {
        Serial.println("MCP/CAN init fail");
        while (1)
            ;
    }
    Serial.println("MCP/CAN init ok at 125kbps with 16MHz clock, accepting any ID");
    CAN.setMode(MCP_NORMAL);
    Serial.println("MCP/CAN set to normal mode");

    delay(SETUP_DELAY_MS);
    Serial.println("\n~~~~\n");

    Serial.println("Setup complete, starting in CAN SNIFFER mode (Blue)");
    board.setColorLED(2, true); // Blue ON
    Serial.println("\n-->> Send 'M1' to switch to CAN SNIFFER mode, 'M2' to RANDOM SEND mode\n\n");
}

// ============================================================================
// LOOP PRINCIPAL
// ============================================================================

void loop()
{
    board.refresh();

    switch (currState)
    {
    case STATE_SNIFFER:
        do_can_sniffer();
        break;
    case STATE_RANDOM_SEND:
        do_can_random_send();
        break;
    }

    if (Serial.available())
    {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "M1" && currState != STATE_SNIFFER)
        {
            Serial.println("\n\n~~~~Setting CAN SNIFFER mode (Blue)~~~~\n");
            currState = STATE_SNIFFER;

            board.setColorLED(2, true);  // Blue ON
            board.setColorLED(3, false); // Green OFF
        }
        else if (cmd == "M2" && currState != STATE_RANDOM_SEND)
        {
            Serial.println("\n\n~~~~Setting RANDOM SEND mode (Green)~~~~\n");
            currState = STATE_RANDOM_SEND;

            board.setColorLED(2, false); // Blue OFF
            board.setColorLED(3, true);  // Green ON
        }
        else if (cmd.startsWith("MODE_"))
        {
            String mode = cmd.substring(5);
            if (mode == "NORMAL")
            {
                CAN.setMode(MCP_NORMAL);
                Serial.println("CAN mode set to NORMAL");
                board.setColorLED(0, false); // normal mode ON with white LED OFF
            }
            else if (mode == "LOOPBACK")
            {
                CAN.setMode(MCP_LOOPBACK);
                Serial.println("CAN mode set to LOOPBACK");
                board.setColorLED(0, true); // loopback mode ON with white LED ON
            }
        }
        else if (cmd.startsWith("SEND_"))
        {
            // Parse SEND_{can_id:x}_{byte1:02x}_{byte2:02x}...
            int first_ = cmd.indexOf('_');
            int second_ = cmd.indexOf('_', first_ + 1);
            if (first_ != -1 && second_ != -1)
            {
                String idStr = cmd.substring(first_ + 1, second_);
                long can_id = strtol(idStr.c_str(), NULL, 16);
                String dataStr = cmd.substring(second_ + 1);
                unsigned char data[8];
                int dataLen = 0;
                int pos = 0;
                while (pos < dataStr.length() && dataLen < 8)
                {
                    int next_ = dataStr.indexOf('_', pos);
                    if (next_ == -1)
                        next_ = dataStr.length();
                    String byteStr = dataStr.substring(pos, next_);
                    data[dataLen++] = strtol(byteStr.c_str(), NULL, 16);
                    pos = next_ + 1;
                }
                if (CAN.sendMsgBuf(can_id, 0, dataLen, data) == CAN_OK)
                {
                    Serial.println("Custom CAN message sent");
                }
                else
                {
                    Serial.println("Error sending custom CAN msg");
                }
            }
        }
        else if (cmd.startsWith("LED_"))
        {
            // Parse LED_{station}_{r}_{g}_{b}
            int parts[4];
            int idx = 0;
            int pos = 4; // After "LED_"
            for (int i = 0; i < 4 && idx < 4; i++)
            {
                int next_ = cmd.indexOf('_', pos);
                if (next_ == -1)
                    next_ = cmd.length();
                parts[idx++] = cmd.substring(pos, next_).toInt();
                pos = next_ + 1;
            }
            if (idx == 4)
            {
                int station = parts[0];
                int r = parts[1], g = parts[2], b = parts[3];
                if (station == GROUP_NUMBER)
                {
                    // Set own NeoPixel
                    npxl.setPixelColor(0, npxl.Color(r * NPXL_BRIGHTNESS, g * NPXL_BRIGHTNESS, b * NPXL_BRIGHTNESS));
                    npxl.show();
                    Serial.println("Own LED updated");
                }
                else
                {
                    // Send remote LED command via CAN, 1JKL 0RGB
                    char ledCmd = 0x80 | ((station << 4) & 0x70) | ((r << 2) & 4) | ((g << 1) & 2) | ((b << 0) & 1);
                    long can_id = 0x100 + GROUP_NUMBER; // sending from own group number
                    if (CAN.sendMsgBuf(can_id, 0, 1, (uint8_t *)(&ledCmd)) == CAN_OK)
                    {
                        Serial.println("LED command sent via CAN");
                    }
                    else
                    {
                        Serial.println("Error sending LED CAN msg");
                    }
                }
            }
        }
    }
}

// ============================================================================
// IMPLEMENTACIÓN - CAN SNIFFER
// ============================================================================

void do_can_sniffer()
{
    if (retryMode)
    {
        exitRetryMode(false);
    }

    if (digitalRead(PIN_MCP_nINT) == LOW)
    {
        long unsigned int rxId;
        unsigned char len = 0;
        unsigned char rxBuf[8];
        if (CAN.readMsgBuf(&rxId, &len, rxBuf) == CAN_OK)
        {
            // Send to GUI over serial
            Serial.print("RXED: ID=0x");
            Serial.print(rxId, HEX);
            Serial.print(" Data=0x");
            for (int i = 0; i < len; i++)
            {
                Serial.print(rxBuf[i], HEX);
            }
            Serial.print("='");
            for (int i = 0; i < len; i++)
            {
                Serial.write(rxBuf[i]);
            }
            Serial.print("' Len=");
            Serial.print(len);
            Serial.println();

            digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
        }
        else
        {
            Serial.println("Error reading CAN msg");
        }
    }
}

// ============================================================================
// IMPLEMENTACIÓN - RANDOM SEND
// ============================================================================

void do_can_random_send()
{
    static uint32_t lastSend[NUM_RANDOM_STATIONS][3];  // [station][angle_type: R=0, C=1, O=2]
    static int16_t lastVal[NUM_RANDOM_STATIONS][3];
    static bool initialized = false;
    static uint32_t nextSendTime = 0;

    if (!initialized)
    {
        memset(lastSend, 0, sizeof(lastSend));
        memset(lastVal, 0, sizeof(lastVal));
        initialized = true;
        nextSendTime = millis() + random(MIN_DELAY_BETWEEN_SEND_MS, MAX_DELAY_BETWEEN_SEND_MS);
    }

    uint32_t now = millis();

    if (retryMode)
    {
        if (now - lastRetryAttempt >= RETRY_INTERVAL_MS)
        {
            lastRetryAttempt = now;

            Serial.print("RETRY: Attempting to resend ID=0x");
            Serial.print(retryId, HEX);
            Serial.print(" Data='");
            Serial.write((const uint8_t *)retryBuffer, retryLen);
            Serial.println("'");

            if (CAN.sendMsgBuf(retryId, 0, retryLen, (uint8_t *)retryBuffer) == CAN_OK)
            {
                exitRetryMode(true);
                digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
            }
            else
            {
                Serial.println("RETRY: Failed, will retry again...");
            }
        }
        return;
    }

    if (now < nextSendTime) return;

    uint8_t randomStation = random(0, NUM_RANDOM_STATIONS);
    long canId = 0x100 + randomStation;

    uint8_t angleType = random(0, 3);
    char angleChars[3] = {'R', 'C', 'O'};
    char angleId = angleChars[angleType];

    int16_t newVal = lastVal[randomStation][angleType] + random(-MAX_DELTA_ANGLE, MAX_DELTA_ANGLE + 1);
    newVal = constrain(newVal, -179, 180);

    // Generate angle value in different valid formats (as per spec):
    // Valid formats: 'R-34', 'C0', 'O67', 'R+138', 'R00', 'C-072', 'R+107', 'O000'
    // Randomly choose format style
    char buf[8];
    int formatStyle = random(0, 6);
    int len;
    
    switch (formatStyle)
    {
        case 0: // Simple format: "R-34" or "C0" (no leading sign for positive, no padding)
            len = snprintf(buf, sizeof(buf), "%c%d", angleId, newVal);
            break;
        case 1: // Explicit sign format: "R+138" (always show sign)
            len = snprintf(buf, sizeof(buf), "%c%+d", angleId, newVal);
            break;
        case 2: // Zero-padded 2 digits: "R00" or "C-07"
            if (newVal >= 0)
                len = snprintf(buf, sizeof(buf), "%c%02d", angleId, newVal);
            else
                len = snprintf(buf, sizeof(buf), "%c%03d", angleId, newVal); // -XX format
            break;
        case 3: // Zero-padded 3 digits: "O000" or "C-072"
            if (newVal >= 0)
                len = snprintf(buf, sizeof(buf), "%c%03d", angleId, newVal);
            else
                len = snprintf(buf, sizeof(buf), "%c%04d", angleId, newVal); // -XXX format
            break;
        case 4: // Explicit positive sign with padding: "R+107"
            len = snprintf(buf, sizeof(buf), "%c%+03d", angleId, newVal);
            break;
        default: // Mix: sometimes simple, sometimes with sign
            if (newVal >= 0 && random(0, 2) == 0)
                len = snprintf(buf, sizeof(buf), "%c%+d", angleId, newVal);
            else
                len = snprintf(buf, sizeof(buf), "%c%d", angleId, newVal);
            break;
    }

    if (CAN.sendMsgBuf(canId, 0, len, (uint8_t *)buf) == CAN_OK)
    {
        Serial.print("SENT ANGLE:");
        Serial.print(" ID=0x");
        Serial.print(canId, HEX);
        Serial.print(" Data=0x");
        for (int i = 0; i < len; i++)
        {
            Serial.print(buf[i], HEX);
        }
        Serial.print("='");
        Serial.write(buf, len);
        Serial.print("' Len=");
        Serial.println(len);

        lastSend[randomStation][angleType] = now;
        lastVal[randomStation][angleType] = newVal;

        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

        // Schedule next send with random delay
        nextSendTime = now + random(MIN_DELAY_BETWEEN_SEND_MS, MAX_DELAY_BETWEEN_SEND_MS);
    }
    else
    {
        Serial.print("Error sending CAN msg: ID=0x");
        Serial.print(canId, HEX);
        Serial.print(" Data=");
        Serial.write(buf, len);
        Serial.println();
        enterRetryMode(canId, buf, len);
    }
}

// ============================================================================
// IMPLEMENTACIÓN - RETRY MODE
// ============================================================================

void enterRetryMode(long canId, const char *data, int len)
{
    if (!retryMode)
    {
        retryMode = true;
        retryId = canId;
        retryLen = len;
        memcpy(retryBuffer, data, len);

        Serial.println("\n~~~~ ENTERING RETRY MODE ~~~~");
        Serial.print("Failed message: ID=0x");
        Serial.print(canId, HEX);
        Serial.print(" Data='");
        Serial.write((const uint8_t *)data, len);
        Serial.println("'");

        board.setColorLED(1, true); // Yellow LED flashing indicates retry
    }
}

void exitRetryMode(bool success)
{
    if (retryMode)
    {
        retryMode = false;

        if (success)
        {
            Serial.println("\n~~~~ EXITING RETRY MODE - SUCCESS ~~~~\n");
        }
        else
        {
            Serial.println("\n~~~~ EXITING RETRY MODE ~~~~\n");
        }

        board.setColorLED(1, false); // Turn off yellow LED
    }
}