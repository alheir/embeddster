#include <Arduino.h>
#include "pin_assignment.h"

#define BAUD_RATE 115200 // explicity defined in platformio.ini

#include <Adafruit_NeoPixel.h>
#define NUMPIXELS 1
Adafruit_NeoPixel npxl(NUMPIXELS, PIN_NPXL, NEO_GRB + NEO_KHZ800);

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
    npxl.setPixelColor(0, npxl.Color(0, 0, 15));
    npxl.show();
    Serial.println("\n-->> Send 'M1' to switch to CAN SNIFFER mode, 'M2' to RANDOM SEND mode\n\n");
}

enum State
{
    STATE_SNIFFER,
    STATE_RANDOM_SEND,
    STATE_N
};

uint8_t currState = STATE_SNIFFER;
uint8_t nextState = STATE_RANDOM_SEND;

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
            Serial.println("\n\n~~~~Switching to CAN SNIFFER mode (Blue)~~~~\n");
            currState = STATE_SNIFFER;
            npxl.setPixelColor(0, npxl.Color(0, 0, 15));
            npxl.show();
        } else if (cmd == "M2" && currState != STATE_RANDOM_SEND) {
            Serial.println("\n\n~~~~Switching to RANDOM SEND mode (Green)~~~~\n");
            currState = STATE_RANDOM_SEND;
            npxl.setPixelColor(0, npxl.Color(0, 15, 0));
            npxl.show();
        }
    }
}

void do_can_sniffer()
{
    if (digitalRead(PIN_MCP_nINT) == LOW)
    {
        long unsigned int rxId;
        unsigned char len = 0;
        unsigned char rxBuf[8];
        if (CAN.readMsgBuf(&rxId, &len, rxBuf) == CAN_OK)
        {
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