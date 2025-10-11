#include <Arduino.h>
#include "pin_assignment.h"

#define BAUD_RATE 115200 // explicity defined in platformio.ini

#include <Adafruit_NeoPixel.h>
#define NUMPIXELS 1
Adafruit_NeoPixel npxl(NUMPIXELS, PIN_NPXL, NEO_GRB + NEO_KHZ800);
#define NPXL_BRIGHTNESS 15

#include <mcp_can.h>
#include <SPI.h>
MCP_CAN CAN(PIN_MCP_nCS);

#include "tp1board.h"
TP1BOARD board;

#define SETUP_DELAY_MS 250

void do_can_sniffer();
void do_can_random_send();

void setup()
{
    Serial.begin(BAUD_RATE);
    Serial.println("\n\n~~~~TP1BOARD CAN SNIFFER/RANDOM SENDER~~~~\n");
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
    for(int i=0; i<3; i++)
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
    board.refresh();
    Serial.println("\n-->> Send 'M1' to switch to CAN SNIFFER mode, 'M2' to RANDOM SEND mode\n\n");
}

enum State
{
    STATE_SNIFFER,
    STATE_RANDOM_SEND,
    STATE_N
};

uint8_t currState = STATE_SNIFFER;  // Default to sniffer
uint8_t nextState = STATE_RANDOM_SEND;

// Add global for LED command handling
#define GROUP_NUMBER 0  // As defined in original

void do_can_sniffer()
{
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

#define GROUP_NUMBER 0 
#define NODE_ID (0x100 + GROUP_NUMBER)
void do_can_random_send()
{
    static uint32_t lastSendR = 0;
    static uint32_t lastSendC = 0;
    static uint32_t lastSendO = 0;
    static int16_t lastValR = 0;
    static int16_t lastValC = 0;
    static int16_t lastValO = 0;
    static uint32_t lastLedSend = 0;
    static uint8_t ledTargetGroup = 1;

    uint32_t now = millis();

    int16_t simR = lastValR + random(-5, 6);
    int16_t simC = lastValC + random(-5, 6);
    int16_t simO = lastValO + random(-5, 6);
    simR = constrain(simR, -180, 180);
    simC = constrain(simC, -180, 180);
    simO = constrain(simO, -180, 180);

    auto sendAngle = [&](char angleId, int16_t val, uint32_t& lastSend, int16_t& lastVal) {
        if (abs(val - lastVal) >= 6 || (now - lastSend) >= 2000) {
            char buf[5];
            int len = snprintf(buf, sizeof(buf), "%c%d", angleId, val);
            if (CAN.sendMsgBuf(NODE_ID, 0, len, (uint8_t*)buf) == CAN_OK) {
                Serial.print("SENT ANGLE: ID=0x");
                Serial.print(NODE_ID, HEX);
                Serial.print(" Data=0x");
                for (int i = 0; i < len; i++) {
                    Serial.print(buf[i], HEX);
                }
                Serial.print("='");
                Serial.write(buf, len);
                Serial.print("' Len=");
                Serial.println(len);
                
                lastSend = now;
                lastVal = val;

                digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
            } else {
                Serial.println("Error sending CAN msg");
            }
        }
    };

    sendAngle('R', simR, lastSendR, lastValR);
    sendAngle('C', simC, lastSendC, lastValC);
    sendAngle('O', simO, lastSendO, lastValO);

    delay(100); // update rate
}

void loop()
{
    switch (currState)
    {
    case STATE_SNIFFER:
        do_can_sniffer();
        break;
    case STATE_RANDOM_SEND:
        do_can_random_send();
        break;
    }

    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "M1" && currState != STATE_SNIFFER) {
            Serial.println("\n\n~~~~Setting CAN SNIFFER mode (Blue)~~~~\n");
            currState = STATE_SNIFFER;

            board.setColorLED(2, true); // Blue ON
            board.setColorLED(3, false); // Green OFF
            board.refresh();

        } else if (cmd == "M2" && currState != STATE_RANDOM_SEND) {
            Serial.println("\n\n~~~~Setting RANDOM SEND mode (Green)~~~~\n");
            currState = STATE_RANDOM_SEND;

            board.setColorLED(2, false); // Blue OFF
            board.setColorLED(3, true); // Green ON
            board.refresh();

        } else if (cmd.startsWith("MODE_")) {
            String mode = cmd.substring(5);
            if (mode == "NORMAL") {
                CAN.setMode(MCP_NORMAL);
                Serial.println("CAN mode set to NORMAL");
                board.setColorLED(0, false); // normal mode ON with white LED OFF
                board.refresh();
            } else if (mode == "LOOPBACK") {
                CAN.setMode(MCP_LOOPBACK);
                Serial.println("CAN mode set to LOOPBACK");
                board.setColorLED(0, true); // loopback mode ON with white LED ON
                board.refresh();
            }
        } else if (cmd.startsWith("SEND_")) {
            // Parse SEND_{can_id:x}_{byte1:02x}_{byte2:02x}...
            int first_ = cmd.indexOf('_');
            int second_ = cmd.indexOf('_', first_ + 1);
            if (first_ != -1 && second_ != -1) {
                String idStr = cmd.substring(first_ + 1, second_);
                long can_id = strtol(idStr.c_str(), NULL, 16);
                String dataStr = cmd.substring(second_ + 1);
                unsigned char data[8];
                int dataLen = 0;
                int pos = 0;
                while (pos < dataStr.length() && dataLen < 8) {
                    int next_ = dataStr.indexOf('_', pos);
                    if (next_ == -1) next_ = dataStr.length();
                    String byteStr = dataStr.substring(pos, next_);
                    data[dataLen++] = strtol(byteStr.c_str(), NULL, 16);
                    pos = next_ + 1;
                }
                if (CAN.sendMsgBuf(can_id, 0, dataLen, data) == CAN_OK) {
                    Serial.println("Custom CAN message sent");
                } else {
                    Serial.println("Error sending custom CAN msg");
                }
            }
        } else if (cmd.startsWith("LED_")) {
            // Parse LED_{station}_{r}_{g}_{b}
            int parts[4];
            int idx = 0;
            int pos = 4;  // After "LED_"
            for (int i = 0; i < 4 && idx < 4; i++) {
                int next_ = cmd.indexOf('_', pos);
                if (next_ == -1) next_ = cmd.length();
                parts[idx++] = cmd.substring(pos, next_).toInt();
                pos = next_ + 1;
            }
            if (idx == 4) {
                int station = parts[0];
                int r = parts[1], g = parts[2], b = parts[3];
                if (station == GROUP_NUMBER) {
                    // Set own NeoPixel
                    npxl.setPixelColor(0, npxl.Color(r * NPXL_BRIGHTNESS, g * NPXL_BRIGHTNESS, b * NPXL_BRIGHTNESS));
                    npxl.show();
                    Serial.println("Own LED updated");
                } else {
                    // Send remote LED command via CAN, 1JKL 0RGB
                    char ledCmd = 0x80 | ((station << 4) & 0x70) | ((r  << 2) & 4) | ((g << 1) & 2) | ((b << 0) & 1);
                    long can_id = 0x100 + GROUP_NUMBER; // sending from own group number
                    if (CAN.sendMsgBuf(can_id, 0, 1, (uint8_t*)(&ledCmd)) == CAN_OK) {
                        Serial.println("LED command sent via CAN");
                    } else {
                        Serial.println("Error sending LED CAN msg");
                    }
                }
            }
        }
    }
}