AVR-UART-Parse-exemple
======================

Parsing UART commands exemple

based on www.adnbr.co.uk/articles/parsing-simple-usart-commands

uses Peter Fleury's uart library http://homepage.hispeed.ch/peterfleury/avr-software.html#libs


To compile
---
Adapt these lines from Makefile to match your configuration:

*main.c*

    #define UART_BAUD_RATE 57600

*Makefile*

    MCU = atmega16
	[...]
    F_CPU = 12000000
	[...]
    AVRDUDE_PORT = /dev/ttyUSB0    # programmer connected to serial device
	[...]
    AVRDUDE_SPEED = 19200
	[...]
    AVRDUDE_FLAGS += -b $(AVRDUDE_SPEED)

And run
	make && make program

To test it 
---
    #Open communication with the microcontroler)
    screen /dev/ttyUSB1 57600 #for exemple with GNU/Linux
	
	#then reset your microcontroler
	#you should see a greeting message with instructions
	
AVR UART  
Command parsing demo  

End each input with enter key  
This demo has two parameters: a and goto  
To set a parameter: a=45 (or any number)  
To query a parameter: a?  
No difference with case: a? is the same thing as A?  
Illegal values set parameter to zero: a=t66  

	#Try these
	a=11<enter> #set parameter
	a?<enter> #query parameter
	A?<enter> #parameter names are case independant
	A=98<enter>
	a?<enter>
	goto?<enter>
	goto=t65<enter> #illegal number
	goto?<enter>
	
