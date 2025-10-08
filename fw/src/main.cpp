#include <Arduino.h>
#include "pin_assignment.h"

#define BAUD_RATE 115200 // explicity defined in platformio.ini

#define BUTTON_BUILTIN 0

#include <Adafruit_NeoPixel.h>
#define NUMPIXELS 1
Adafruit_NeoPixel npxl(NUMPIXELS, PIN_NPXL, NEO_GRB + NEO_KHZ800);

#include <mcp_can.h>
#include <SPI.h>
MCP_CAN CAN(PIN_MCP_nCS);

#include "tp1board.h"
TP1BOARD board;

void do_can_sniffer();
void do_can_random_send();

void setup()
{
    Serial.begin(BAUD_RATE);
    Serial.println("Serial init ok");

    delay(500);

    pinMode(BUTTON_BUILTIN, INPUT_PULLUP);
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Onboard LED and button init ok");

    delay(500);

    if (!npxl.begin())
    {
        Serial.println("NEOPIXEL init fail");
        while (1)
            ;
    }
    Serial.println("NEOPIXEL init ok");
    npxl.setPixelColor(0, npxl.Color(255, 0, 0));
    npxl.show();
    Serial.println("NEOPIXEL set to red");

    board.begin();
    Serial.println("TP1BOARD init ok");

    pinMode(PIN_MCP_nINT, INPUT);
    if (CAN.begin(MCP_ANY, CAN_125KBPS, MCP_16MHZ) == CAN_FAILINIT)
    {
        Serial.println("MCP/CAN init fail");
        while (1)
            ;
    }
    Serial.println("MCP/CAN init ok at 125kbps with 16MHz clock, aceptting any ID");
    CAN.setMode(MCP_NORMAL);
    Serial.println("MCP/CAN set to normal mode");

    delay(500);
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

    if (!digitalRead(BUTTON_BUILTIN))
    {
        Serial.print("\n\n~~~~Switching to  ");
        Serial.print(nextState ? "RANDOM SEND" : "CAN SNIFFER");
        Serial.println("~~~~\n");
        currState = nextState;
        nextState = (nextState + 1) % STATE_N;

        while (!digitalRead(BUTTON_BUILTIN))
            ;
        delay(50);
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
            int len = sprintf(buf, "%c%d", angleId, val);
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