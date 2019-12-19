
/* 
	HHLib programming library for HydraHarp 400
	PicoQuant GmbH, 

    Ver. 3.0.0.2     March 2019
*/


#define LIB_VERSION "3.0"	

#define MAXDEVNUM	8		// max num of USB devices
 
#define HHMAXINPCHAN   8	// max num of physicl input channels

#define BINSTEPSMAX	26	    // get actual number via HH_GetBaseResolution() !

#define MAXHISTLEN  65536	// max number of histogram bins
#define MAXLENCODE  6		// max length code histo mode

#define MAXHISTLEN_CONT	8192	// max number of histogram bins in continuous mode
#define MAXLENCODE_CONT	3		// max length code in continuous mode

#define MAXCONTMODEBUFLEN	 262272   //bytes of buffer needed for HH_GetContModeBlock

#define TTREADMAX   131072  // 128K event records can be read in one chunk
#define TTREADMIN   128     // 128 records = minimum buffer size that must be provided

#define MODE_HIST	0
#define MODE_T2		2
#define MODE_T3		3
#define MODE_CONT	8

#define MEASCTRL_SINGLESHOT_CTC			0 //default
#define MEASCTRL_C1_GATED				1
#define MEASCTRL_C1_START_CTC_STOP		2
#define MEASCTRL_C1_START_C2_STOP		3
//continuous mode only
#define MEASCTRL_CONT_C1_GATED			4
#define MEASCTRL_CONT_C1_START_CTC_STOP	5
#define MEASCTRL_CONT_CTC_RESTART		6

#define EDGE_RISING   1
#define EDGE_FALLING  0

#define FEATURE_DLL       0x0001
#define FEATURE_TTTR      0x0002
#define FEATURE_MARKERS   0x0004 
#define FEATURE_LOWRES    0x0008 
#define FEATURE_TRIGOUT   0x0010

#define FLAG_OVERFLOW     0x0001  //histo mode only
#define FLAG_FIFOFULL     0x0002  
#define FLAG_SYNC_LOST    0x0004  
#define FLAG_REF_LOST     0x0008  
#define FLAG_SYSERROR     0x0010  //hardware error, must contact support
#define FLAG_ACTIVE       0x0020  //measurement is running

#define SYNCDIVMIN		1
#define SYNCDIVMAX		16

#define ZCMIN		0			//mV
#define ZCMAX		40			//mV 
#define DISCRMIN	0			//mV
#define DISCRMAX	1000		//mV 

#define CHANOFFSMIN -99999		//ps
#define CHANOFFSMAX  99999		//ps

#define OFFSETMIN	0			//ps
#define OFFSETMAX	500000		//ns 
#define ACQTMIN		1			//ms
#define ACQTMAX		360000000	//ms  (100*60*60*1000ms = 100h)

#define STOPCNTMIN  1
#define STOPCNTMAX  4294967295  //32 bit is mem max

#define HOLDOFFMIN  0			//ns
#define HOLDOFFMAX  524296		//ns


//The following are bitmasks for return values from GetWarnings()

#define WARNING_SYNC_RATE_ZERO				0x0001
#define WARNING_SYNC_RATE_TOO_LOW			0x0002
#define WARNING_SYNC_RATE_TOO_HIGH			0x0004

#define WARNING_INPT_RATE_ZERO				0x0010
#define WARNING_INPT_RATE_TOO_HIGH			0x0040

#define WARNING_INPT_RATE_RATIO				0x0100
#define WARNING_DIVIDER_GREATER_ONE			0x0200
#define WARNING_TIME_SPAN_TOO_SMALL			0x0400
#define WARNING_OFFSET_UNNECESSARY			0x0800
