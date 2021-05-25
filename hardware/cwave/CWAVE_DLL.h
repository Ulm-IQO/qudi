#ifndef _C_CWAVEDLL_H
#define _C_CWAVEDLL_H

#include "stdint.h"

#ifdef __cplusplus
extern "C" {
#endif

	// export or import the symbols as appropriate
#define LIB_EXPORT __declspec(dllexport)

	/***********************************************
	*
	*	C variable definitions.
	*
	************************************************/


	/***********************************************
	*
	*	C function declarations.
	*
	************************************************/
	LIB_EXPORT int DLL_Version();
	LIB_EXPORT int DLL_WLM_Version();
	
	LIB_EXPORT  int cwave_connect(char* ipAddress);
	LIB_EXPORT  void cwave_disconnect();
	LIB_EXPORT	void library_init();
	LIB_EXPORT  int admin_elevate(char* password);

	LIB_EXPORT  int cwave_updatestatus();
	LIB_EXPORT  int is_ready();

	LIB_EXPORT  int get_intvalue(char* cmd);
	LIB_EXPORT  double get_floatvalue(char* cmd);
	LIB_EXPORT  int get_photodiode_laser();
	LIB_EXPORT  int get_photodiode_opo();
	LIB_EXPORT  int get_photodiode_shg();
	LIB_EXPORT  int get_photodiode_4();
	LIB_EXPORT  int get_statusbits();
	LIB_EXPORT	int get_status_laser();
	LIB_EXPORT	int get_status_temp_ref();
	LIB_EXPORT	int get_status_temp_opo();
	LIB_EXPORT	int get_status_temp_shg();
	LIB_EXPORT	int get_status_lock_opo();
	LIB_EXPORT	int get_status_lock_shg();
	LIB_EXPORT	int get_status_lock_etalon();
	LIB_EXPORT  int ext_get_intvalue(char* cmd);
	LIB_EXPORT  double ext_get_floatvalue(char* cmd);

	LIB_EXPORT  int set_intvalue(char* cmd, int value);
	LIB_EXPORT	int set_floatvalue(char* cmd, double value);
	LIB_EXPORT  int ext_set_command(char* cmd);
	LIB_EXPORT  int set_command(char* cmd);

	LIB_EXPORT	void WLM_PID_Compute(double measurement);

	LIB_EXPORT	int set_regopo_extramp(int duration, int mode, int lowerLimit, int upperLimit);

#ifdef __cplusplus
}
#endif
#endif // !_C_CWAVEDLL_H
