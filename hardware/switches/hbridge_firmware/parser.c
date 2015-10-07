#include "parser.h"

unsigned char data_count = 0;
unsigned char data_in[8];
char command_in[8];

volatile unsigned char variable_P1 = 0;
volatile unsigned char variable_P2 = 0;
volatile unsigned char variable_P3 = 0;
volatile unsigned char variable_P4 = 0;
volatile unsigned int switch_time = 300;

int parse_assignment (char input[16]) {
  char *pch;
  char cmdValue[16];
  // Find the position the equals sign is
  // in the string, keep a pointer to it
  pch = strchr(input, '=');
  // Copy everything after that point into
  // the buffer variable
  strcpy(cmdValue, pch+1);
  // Now turn this value into an integer and
  // return it to the caller.
  return atoi(cmdValue);
}

void copy_command () {
  // Copy the contents of data_in into command_in
  memcpy(command_in, data_in, 8);
  // Now clear data_in, the UART can reuse it now
  memset(data_in, 0, 8);
}

void process_command() {
  if(strcasestr(command_in, "P1") != NULL) {
    if(strcasestr(command_in,"?") != NULL) {
      print_value("P1", variable_P1);
    } else {
      variable_P1 = parse_assignment(command_in);
      if(variable_P1) {
          push_h(1);
      } else {
          pull_h(1);
      }
      print_value("P1", variable_P1);
    }
  }
  else if(strcasestr(command_in, "P2") != NULL) {
    if(strcasestr(command_in,"?") != NULL) {
      print_value("P2", variable_P2);
    } else { 
      variable_P2 = parse_assignment(command_in);
      if(variable_P2) {
          push_h(2);
      } else {
          pull_h(2);
      }
      print_value("P2", variable_P2);
    }
  }
  else if(strcasestr(command_in, "P3") != NULL) {
    if(strcasestr(command_in,"?") != NULL) {
      print_value("P3", variable_P3);
    } else {
      variable_P3 = parse_assignment(command_in);
      if(variable_P3) {
          push_h(3);
      } else {
          pull_h(3);
      }
      print_value("P3", variable_P3);
    }
  }
  else if(strcasestr(command_in, "P4") != NULL) {
    if(strcasestr(command_in,"?") != NULL) {
      print_value("P4", variable_P4);
    } else {
      variable_P4 = parse_assignment(command_in);
      if(variable_P4) {
          push_h(4);
      } else {
          pull_h(4);
      }
      print_value("P4", variable_P4);
    }
  }
  else if(strcasestr(command_in, "STATUS") != NULL) {
    print_raw(variable_P1);
    uart_puts(" ");
    print_raw(variable_P2);
    uart_puts(" ");
    print_raw(variable_P3);
    uart_puts(" ");
    print_raw(variable_P4);
    uart_puts(RETURN_NEWLINE);
  }
  else if(strcasestr(command_in, "SWITCHTIME") != NULL) {
    if(strcasestr(command_in,"?") != NULL) {
      print_value("SWITCHTIME", switch_time);
    } else {
      switch_time = parse_assignment(command_in);
      print_value("SWITCHTIME", switch_time);
    }
  }
  else if(strcasestr(command_in, "INIT") != NULL) {
      uart_puts(RETURN_NEWLINE);
      uart_puts("Quad H-Bridge Controller FW 0.0.9");
      uart_puts(RETURN_NEWLINE);
      uart_puts("ready.");
      uart_puts(RETURN_NEWLINE);
  }
}

void print_value (char *id, int value) {
  char buffer[8];
  itoa(value, buffer, 10);
  uart_puts(id);
  uart_putc('=');
  uart_puts(buffer);
  uart_puts(RETURN_NEWLINE);
}

void print_raw (int value) {
  char buffer[8];
  itoa(value, buffer, 10);
  uart_puts(buffer);
}

void uart_ok() {
  uart_puts("OK");
  uart_puts(RETURN_NEWLINE);
}

void process_uart(){
  /* Get received character from ringbuffer
   * uart_getc() returns in the lower byte the received character and 
   * in the higher byte (bitmask) the last receive error
   * UART_NO_DATA is returned when no data is available.   */
  unsigned int c = uart_getc();
  
  if ( c & UART_NO_DATA ){
    // no data available from UART 
  }
  else {
    // new data available from UART check for Frame or Overrun error
    if ( c & UART_FRAME_ERROR ) {
      /* Framing Error detected, i.e no stop bit detected */
      uart_puts_P("UART Frame Error: ");
    }
    if ( c & UART_OVERRUN_ERROR ) {
      /* Overrun, a character already present in the UART UDR register was 
       * not read by the interrupt handler before the next character arrived,
       * one or more received characters have been dropped */
      uart_puts_P("UART Overrun Error: ");
    }
    if ( c & UART_BUFFER_OVERFLOW ) {
      /* We are not reading the receive buffer fast enough,
       * one or more received character have been dropped  */
      uart_puts_P("Buffer overflow error: ");
    }
    
    // Add char to input buffer
    data_in[data_count] = c;
    
    // Return is signal for end of command input
    if (data_in[data_count] == CHAR_RETURN) {
      // Reset to 0, ready to go again
      data_count = 0;
      //uart_puts(RETURN_NEWLINE);
      
      copy_command();
      process_command();
      //uart_ok();
    } 
    else {
      data_count++;
    }
    
    //uart_putc( (unsigned char)c );
  }
}

