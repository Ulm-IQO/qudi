#include "hardware.h"

void initialize() {
    DDRB |= (1<<PB0)|(1<<PB1);
	PORTB |= (1<<PB2) | (1<<PB3) | (1<<PB4)| (1<<PB5);
	DDRC |= (1<<PC0) | (1<<PC1) | (1<<PC2) | (1<<PC3) | (1<<PC4)| (1<<PC5);
	PORTC = 0x00;
	DDRD |= (1<<PD4) | (1<<PD5) | (1<<PD6) | (1<<PD7);
	PORTD &= ~( (1<<PD6) | (1<<PD7) );
	PORTD |= (1<<PD3);

	/* Set up timer1 for PWM (it's also used for button debouncing) */
	TCCR1A |= (1<<WGM10) ;
	TCCR1B |= (1<<CS10) | (1<<CS11);

	/* Enable the timer1 overflow interrupt */
	TIMSK = (1 << TOIE1);
}

void push_h(char nr) {
	switch (nr ){
		case 1:
			CW1 = ON;
			vardelay1ms(switch_time);
			CW1 = OFF;
			variable_P1 = 1;
			break;
		case 2:
			CW2 = ON;
			vardelay1ms(switch_time);
			CW2 = OFF;
			variable_P2 = 1;
			break;
		case 3:
			CW3 = ON;
			vardelay1ms(switch_time);
			CW3 = OFF;
			variable_P3 = 1;
			break;
		case 4:
			CW4 = ON;
			vardelay1ms(switch_time);
			CW4 = OFF;
			variable_P4 = 1;
			break;
		default:
			break;
	}
}

void pull_h(char nr) {
	switch (nr ){
		case 1:
			CCW1 = ON;
			vardelay1ms(switch_time);
			CCW1 = OFF;
			variable_P1 = 0;
			break;
		case 2:
			CCW2 = ON;
			vardelay1ms(switch_time);
			CCW2 = OFF;
			variable_P2 = 0;
			break;
		case 3:
			CCW3 = ON;
			vardelay1ms(switch_time);
			CCW3 = OFF;
			variable_P3 = 0;
			break;
		case 4:
			CCW4 = ON;
			vardelay1ms(switch_time);
			CCW4 = OFF;
			variable_P4 = 0;
			break;
		default:
			break;
	}
}

void vardelay1ms(unsigned int delay) {
	while(delay--){
		_delay_ms(1);
	}
}

ISR(TIMER1_OVF_vect) {
        static unsigned char count1, count2, count3, count4;
        /* Button 1 */
        if (BUTTON1_RAW) {
                /* Button is pressed: indicate immediately */
                button_states |= 1;
                count1 = DEBOUNCE_COUNT;
        } else {
                /* Button is released: Wait for several contiguous samples before changing the flag */
                if (count1 == 0) {
                        button_states &= ~1;
                } else {
                        count1--;
                }
        }
        /* Button 2 */
        if (BUTTON2_RAW) {
                /* Button is pressed: indicate immediately */
                button_states |= 2;
                count2 = DEBOUNCE_COUNT;
        } else {
                /* Button is released: Wait for several contiguous samples before changing the flag */
                if (count2 == 0) {
                        button_states &= ~2;
                } else {
                        count2--;
                }
        }
        /* Button 3 */
        if (BUTTON3_RAW) {
                /* Button is pressed: indicate immediately */
                button_states |= 4;
                count3 = DEBOUNCE_COUNT;
        } else {
                /* Button is released: Wait for several contiguous samples before changing the flag */
                if (count3 == 0) {
                        button_states &= ~4;
                } else {
                        count3--;
                }
        }
        /* Button 4 */
        if (BUTTON4_RAW) {
                /* Button is pressed: indicate immediately */
                button_states |= 8;
                count4 = DEBOUNCE_COUNT;
        } else {
                /* Button is released: Wait for several contiguous samples before changing the flag */
                if (count4 == 0) {
                        button_states &= ~8;
                } else {
                        count4--;
                }
        }
}

