#ifndef UARTPARSER_H
#define UARTPARSER_H

#include <stdlib.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <string.h>

#include "uart.h"

#define TRUE 1
#define FALSE 0
#define CHAR_NEWLINE '\n'
#define CHAR_RETURN '\r'
#define RETURN_NEWLINE "\r\n"

void copy_command (void);

void process_command (void);

void print_value (char *id, int value);

void uart_ok (void);

int parse_assignment (char input[16]);

void process_uart (void);

extern volatile unsigned char variable_P1;
extern volatile unsigned char variable_P2;
extern volatile unsigned char variable_P3;
extern volatile unsigned char variable_P4;
extern volatile unsigned int switch_time;

#endif /* UARTPARSER_H */
