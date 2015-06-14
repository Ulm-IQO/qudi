/*************************************************************************
Parsing UART commands exemple

based on www.adnbr.co.uk/articles/parsing-simple-usart-commands

uses Peter Fleury's uart library http://homepage.hispeed.ch/peterfleury/avr-software.html#libs
for easier microcontroler change.
*************************************************************************/

#define UART_BAUD_RATE 9600 //uart speed

#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>
#include "uart.h"
#include "parser.h"
#include "hardware.h"
#include "main.h"

int main(void) { 
  initialize();
  /*  Initialize UART library, pass baudrate and AVR cpu clock
   *  with the macro 
   *  UART_BAUD_SELECT() (normal speed mode )
   *  or 
   *  UART_BAUD_SELECT_DOUBLE_SPEED() ( double speed mode)  */
  uart_init( UART_BAUD_SELECT(UART_BAUD_RATE, F_CPU) ); 
  
  // now enable interrupt, since UART library is interrupt controlled
  sei();
  
  /*  Transmit string to UART
   *  The string is buffered by the uart library in a circular buffer
   *  and one character at a time is transmitted to the UART using interrupts.
   *  uart_puts() blocks if it can not write the whole string to the circular 
   *  buffer */

  uart_puts(RETURN_NEWLINE);
  uart_puts("Quad H-Bridge Controller FW 0.0.9");
  uart_puts(RETURN_NEWLINE);
  uart_puts("ready.");
  uart_puts(RETURN_NEWLINE);

  unsigned char cur_button_states, last_button_states, button_press;
  /* Used to detect button presses */
	last_button_states = 0;

  while (1) {
    process_uart();
    /* Button press logic */

    /* Read this once in case it changes during the code later.
     * After this line, don't read button_states again because it
     * may be different.
     */
    cur_button_states = button_states;

    /* Determine which buttons have been pressed.
     * Each bit in button_press will be set if the corresponding button
     * is pressed on this iteration but wasn't on the last iteration.
     */
    button_press = cur_button_states & ~last_button_states;
    /* Save button states for the next iteration */
    last_button_states = cur_button_states;
    /* This is only done for readability.  It would be more efficient to
     * use the bitfields in button_press directly, perhaps with defines.
     */
    if( button_press & 1 ) {
		if(variable_P1) {
			pull_h(1);
		} else {
			push_h(1);
		}
	}
    if( button_press & 2 ) {
		if(variable_P2) {
			pull_h(2);
		} else {
			push_h(2);
		}
	}
    if( button_press & 4 ) {
		if(variable_P3) {
			pull_h(3);
		} else {
			push_h(3);
		}
	}
    if( button_press & 8 ) {
		if(variable_P4) {
			pull_h(4);
		} else {
			push_h(4);
		}
	}

	LED1 = variable_P1 ? ON : OFF ;
	LED2 = variable_P2 ? ON : OFF ;
	LED3 = variable_P3 ? ON : OFF ;
	LED4 = variable_P4 ? ON : OFF ;
  } 
}
