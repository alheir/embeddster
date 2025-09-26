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

void setup()
{
    Serial.begin(BAUD_RATE);
    Serial.println("Serial init ok");

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

    delay(500);

    if (CAN.begin(MCP_ANY, CAN_125KBPS, MCP_8MHZ) == CAN_FAILINIT)
    {
        Serial.println("MCP/CAN init fail");
        while (1)
            ;
    }
    Serial.println("MCP/CAN init ok at 125kbps with 8MHz clock, aceptting any ID");
    CAN.setMode(MCP_NORMAL);
    Serial.println("MCP/CAN set to normal mode");

    delay(500);

    board.begin();
    Serial.println("TP1BOARD init ok");
}

void loop()
{
    // Example: Call board.refresh() periodically here if needed
    board.refresh();
}
}
