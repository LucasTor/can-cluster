// esp32_egt4 — emulate a FuelTech EGT-4 CAN module on the FTCAN 2.0 bus.
//
// Broadcasts the EGT-4 SIMPLIFIED packet (Protocol_FTCAN20.pdf p25-26 — the
// authoritative spec, not the buggy "Example 5" on p32):
//   29-bit ID = 0x02400000 (extended), DLC 8. Frame ID selects the module model:
//     A 0x02400000, B 0x02480000, C 0x02500000, D 0x02580000.
//   Payload = 4 x int16, big-endian, signed: channels 1..4 at bytes 0-1/2-3/4-5/6-7.
//   Scale = 0.125 C/bit (value = degC * 8). Range -50..1000 C; error/disconnect 0x2000.
//   CONFIRMED: the FT600 binds model A (0x02400000).
//
// This stub sends fixed temps 100/200/300/400 C so you can confirm the ECU sees the
// channels before wiring real thermocouples.
//
// Uses the ESP32's built-in TWAI (CAN 2.0B) controller. Final-build transceiver:
// TJA1051T/3 with VIO=3.3V (logic) and VDD=5V (bus). 120R termination if at a bus end.
//
// Do NOT run this alongside a real FuelTech EGT-4 module (same ID would collide).

#include "driver/twai.h"

// --- FTCAN EGT-4 simplified-packet broadcast ---
#define EGT_CAN_ID   0x02400000u      // extended 29-bit ID, EGT-4 model A (confirmed)
#define TEMP_SCALE   8                // value = degC * 8  (0.125 C/bit, per p25 spec)

// CAN transceiver wiring (set to your board's pins)
#define CAN_TX_PIN   GPIO_NUM_5
#define CAN_RX_PIN   GPIO_NUM_4

static inline void put_be16(uint8_t *p, int16_t v) {   // big-endian, signed
  p[0] = (uint8_t)(v >> 8);
  p[1] = (uint8_t)(v & 0xFF);
}

void setup() {
  Serial.begin(115200);

  twai_general_config_t g = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  twai_timing_config_t  t = TWAI_TIMING_CONFIG_1MBITS();   // FTCAN = 1 Mbit/s
  twai_filter_config_t  f = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  if (twai_driver_install(&g, &t, &f) == ESP_OK && twai_start() == ESP_OK)
    Serial.println("TWAI up @ 1Mbit/s");
  else
    Serial.println("TWAI init failed");
}

void loop() {
  const int16_t temps[4] = {100, 200, 300, 400};   // degC, channels 1..4

  twai_message_t msg = {};
  msg.identifier       = EGT_CAN_ID;
  msg.extd             = 1;            // 29-bit extended ID
  msg.data_length_code = 8;
  for (int i = 0; i < 4; i++)
    put_be16(&msg.data[i * 2], (int16_t)(temps[i] * TEMP_SCALE));

  twai_transmit(&msg, pdMS_TO_TICKS(10));   // fire and forget; auto-retransmits on arbitration loss
  delay(20);                                // ~50 Hz broadcast
}
