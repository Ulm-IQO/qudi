#ifndef HARDWARE_H
#define HARDWARE_H

#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <string.h>

#include "uart.h"
#include "parser.h"

/* These definitions make code more readable for active low I/O.
 *
 * The LEDs are connected between the I/O pin and Vcc, so 0 turns them on.
 * Buttons are connected to GND with a pull-up in the chip.  Pressing the
 * button makes the pin go low.
 */
#define ON		0
#define OFF		1

/* Provides access to the bits in a byte. */
typedef struct
{
	char bit_0:1;
	char bit_1:1;
	char bit_2:1;
	char bit_3:1;
	char bit_4:1;
	char bit_5:1;
	char bit_6:1;
	char bit_7:1;
} __bits;

/* Provides a __bits structure at the given address. */
#define IO_BITS(addr)	(*(volatile __bits *)addr)

#define DEBOUNCE_COUNT         5

#define BUTTON1_RAW  (!(PINB & (1 << 2)))
#define BUTTON2_RAW  (!(PINB & (1 << 5)))
#define BUTTON3_RAW  (!(PINB & (1 << 4)))
#define BUTTON4_RAW  (!(PINB & (1 << 3)))

#define BUTTON1		(button_states & 1)
#define BUTTON2		(button_states & 2)
#define BUTTON3		(button_states & 4)
#define BUTTON4		(button_states & 8)

/* LEDs - set to ON or OFF */
#define LED1		IO_BITS(0x32).bit_6
#define LED2		IO_BITS(0x32).bit_7
#define LED3		IO_BITS(0x38).bit_0
#define LED4		IO_BITS(0x38).bit_1

#define CCW1	IO_BITS(0x35).bit_4
#define CW1		IO_BITS(0x35).bit_5

#define CCW2	IO_BITS(0x35).bit_2
#define CW2		IO_BITS(0x35).bit_3

#define CCW3	IO_BITS(0x35).bit_0
#define CW3		IO_BITS(0x35).bit_1

#define CCW4	IO_BITS(0x32).bit_5
#define CW4		IO_BITS(0x32).bit_4

/* Where the debounced button states are actually stored.
 * Button states are bits in this variable.
 * Use BUTTON1 and BUTTON2 to get the bits.
 *
 * You can use this variable to quickly find changes in button
 * states using boolean operators.
 *
 * Don't ever change the value of this variable.  It gets set
 * frequently by an interrupt handler.
 */
volatile unsigned char button_states;

void initialize(void);

void pull_h(char);

void push_h(char); 

void vardelay1ms(unsigned int);

#endif /* HARDWARE_H */
