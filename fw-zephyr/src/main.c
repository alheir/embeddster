/*
 * Embeddster Zephyr spike: boot, MCP2515 loopback self-test, then CAN sniffer.
 * Serial line format matches gui/src/protocol/protocol_handler.py (RXED: ...).
 */

#include <stdio.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/can.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

/* -------------------------------------------------------------------------- */
/* Configuration                                                              */
/* -------------------------------------------------------------------------- */

#define TEST_CAN_ID     0x100U
#define RX_MSGQ_DEPTH   8

/* -------------------------------------------------------------------------- */
/* Module state                                                               */
/* -------------------------------------------------------------------------- */

CAN_MSGQ_DEFINE(rx_msgq, RX_MSGQ_DEPTH);

static const struct device *const can_dev =
	DEVICE_DT_GET(DT_CHOSEN(zephyr_canbus));

static const struct gpio_dt_spec led =
	GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios);

/* -------------------------------------------------------------------------- */
/* Forward declarations                                                       */
/* -------------------------------------------------------------------------- */

static void print_rxed_line(const struct can_frame *frame);
static int add_rx_filter(void);
static int init_onboard_led(void);
static int run_loopback_self_test(void);
static int start_normal_sniffer(void);

/* -------------------------------------------------------------------------- */
/* Entry point                                                                */
/* -------------------------------------------------------------------------- */

int main(void)
{
	struct can_frame frame;
	int ret;

	printf("\n\n~~~~ Embeddster Zephyr CAN spike ~~~~\n");
	printf("Serial init ok\n");

	ret = init_onboard_led();
	if (ret < 0) {
		printf("Onboard LED init failed: %d\n", ret);
	}

	if (!device_is_ready(can_dev)) {
		printf("MCP2515/CAN device not ready\n");
		return 0;
	}

	printf("MCP/CAN init ok at 125kbps with 16MHz clock\n");

	ret = run_loopback_self_test();
	if (ret != 0) {
		printf("Spike aborted during loopback test\n");
		return 0;
	}

	ret = start_normal_sniffer();
	if (ret != 0) {
		printf("Spike aborted entering sniffer mode\n");
		return 0;
	}

	while (true) {
		ret = k_msgq_get(&rx_msgq, &frame, K_FOREVER);
		if (ret != 0) {
			continue;
		}

		print_rxed_line(&frame);

		if (gpio_is_ready_dt(&led)) {
			gpio_pin_toggle_dt(&led);
		}
	}

	return 0;
}

/* -------------------------------------------------------------------------- */
/* Serial output                                                              */
/* -------------------------------------------------------------------------- */

static void print_rxed_line(const struct can_frame *frame)
{
	printf("RXED: ID=0x%X Data=0x", frame->id);

	for (int i = 0; i < frame->dlc; i++) {
		printf("%02X", frame->data[i]);
	}

	printf("='");
	for (int i = 0; i < frame->dlc; i++) {
		putchar(frame->data[i]);
	}

	printf("' Len=%u\n", frame->dlc);
}

/* -------------------------------------------------------------------------- */
/* GPIO                                                                       */
/* -------------------------------------------------------------------------- */

static int init_onboard_led(void)
{
	if (!gpio_is_ready_dt(&led)) {
		printf("Onboard LED not ready\n");
		return -ENODEV;
	}

	const int ret = gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE);

	if (ret < 0) {
		return ret;
	}

	printf("Onboard LED init ok\n");
	return 0;
}

/* -------------------------------------------------------------------------- */
/* CAN                                                                        */
/* -------------------------------------------------------------------------- */

static int add_rx_filter(void)
{
	const struct can_filter filter = {
		.flags = 0U,
		.id = 0U,
		.mask = 0U,
	};

	return can_add_rx_filter_msgq(can_dev, &rx_msgq, &filter);
}

static int run_loopback_self_test(void)
{
	struct can_frame tx_frame = {
		.flags = 0U,
		.id = TEST_CAN_ID,
		.dlc = 4U,
	};
	struct can_frame rx_frame;
	int ret;

	memcpy(tx_frame.data, "R-10", tx_frame.dlc);

	ret = can_set_mode(can_dev, CAN_MODE_LOOPBACK);
	if (ret != 0) {
		printf("CAN loopback mode failed: %d\n", ret);
		return ret;
	}

	ret = can_start(can_dev);
	if (ret != 0) {
		printf("CAN start failed: %d\n", ret);
		return ret;
	}

	ret = add_rx_filter();
	if (ret < 0) {
		printf("RX filter setup failed: %d\n", ret);
		return ret;
	}

	ret = can_send(can_dev, &tx_frame, K_MSEC(100), NULL, NULL);
	if (ret != 0) {
		printf("CAN loopback send failed: %d\n", ret);
		return ret;
	}

	ret = k_msgq_get(&rx_msgq, &rx_frame, K_MSEC(500));
	if (ret != 0) {
		printf("CAN loopback receive timeout: %d\n", ret);
		return ret;
	}

	printf("Loopback self-test OK\n");
	print_rxed_line(&rx_frame);

	ret = can_stop(can_dev);
	if (ret != 0) {
		printf("CAN stop failed: %d\n", ret);
		return ret;
	}

	return 0;
}

static int start_normal_sniffer(void)
{
	int ret;

	ret = can_set_mode(can_dev, CAN_MODE_NORMAL);
	if (ret != 0) {
		printf("CAN normal mode failed: %d\n", ret);
		return ret;
	}

	ret = can_start(can_dev);
	if (ret != 0) {
		printf("CAN start failed: %d\n", ret);
		return ret;
	}

	ret = add_rx_filter();
	if (ret < 0) {
		printf("RX filter setup failed: %d\n", ret);
		return ret;
	}

	printf("Listening on CAN bus (125 kbit/s)...\n");
	return 0;
}
