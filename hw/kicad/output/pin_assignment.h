#ifndef PIN_ASSIGNMENT_H
#define PIN_ASSIGNMENT_H

// SPI / MCP pins
#define PIN_MCP_MOSI 23
#define PIN_MCP_MISO 19
#define PIN_MCP_SCK 18
#define PIN_MCP_nCS 5
#define PIN_MCP_nINT 17

// WS2812B
#define PIN_NPXL 21

// Encoder
#define PIN_ENC_A 4
#define PIN_ENC_B 16
#define PIN_ENC_SW 22

// 74HC595 control pins
#define PIN_595_SI 32
#define PIN_595_SHIFT_CLK 27
#define PIN_595_LATCH_CLK 33
#define PIN_595_nOE 25
#define PIN_595_nRST 26

// 74HC595 outputs: indices para los 16 Qx (primer 74HC595 = QA0..QH0, segundo = QA1..QH1)
typedef enum {
    SR_QA0 = 0,
    SR_QB0,
    SR_QC0,
    SR_QD0,
    SR_QE0,
    SR_QF0,
    SR_QG0,
    SR_QH0,
    SR_QA1,
    SR_QB1,
    SR_QC1,
    SR_QD1,
    SR_QE1,
    SR_QF1,
    SR_QG1,
    SR_QH1
} sr_out_t;

// Bit helper: produce máscara para un índice SR_*
#define SR_BIT(n) ((uint16_t)1u << (n))

// Mapeo semántico (las constantes originales apuntando a QA0..QH1)
#define SEG_DP_BIT  SR_BIT(SR_QA0)  // QA0
#define SEG_G_BIT   SR_BIT(SR_QB0)  // QB0
#define SEG_F_BIT   SR_BIT(SR_QC0)  // QC0
#define SEG_E_BIT   SR_BIT(SR_QD0)  // QD0
#define SEG_D_BIT   SR_BIT(SR_QE0)  // QE0
#define SEG_C_BIT   SR_BIT(SR_QF0)  // QF0
#define SEG_B_BIT   SR_BIT(SR_QG0)  // QG0
#define SEG_A_BIT   SR_BIT(SR_QH0)  // QH0

#define SEL_0_BIT    SR_BIT(SR_QA1) // QA1
#define SEL_1_BIT    SR_BIT(SR_QB1) // QB1
#define STATUS_0_BIT SR_BIT(SR_QC1) // QC1
#define STATUS_1_BIT SR_BIT(SR_QD1) // QD1
#define LED_D3_BIT   SR_BIT(SR_QE1) // QE1
#define LED_D4_BIT   SR_BIT(SR_QF1) // QF1
#define LED_D5_BIT   SR_BIT(SR_QG1) // QG1
#define LED_D6_BIT   SR_BIT(SR_QH1) // QH1

// Ejemplo de uso:
// uint16_t outputs = SEG_A_BIT | SEG_B_BIT | SEL_0_BIT;
// shift_out_16bits(outputs); // función que hace shift/latch hacia los 74HC595

#endif // PIN_ASSIGNMENT_H
