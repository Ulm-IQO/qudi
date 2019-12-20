/* Functions exported by the HydraHarp programming library HHLib*/

/* Ver. 3.0.0.2     March 2019 */

#ifndef _WIN32
#define _stdcall
#endif

extern int _stdcall HH_GetLibraryVersion(char* vers);
extern int _stdcall HH_GetErrorString(char* errstring, int errcode);

extern int _stdcall HH_OpenDevice(int devidx, char* serial); 
extern int _stdcall HH_CloseDevice(int devidx);  
extern int _stdcall HH_Initialize(int devidx, int mode, int refsource);

//all functions below can only be used after HH_Initialize

extern int _stdcall HH_GetHardwareInfo(int devidx, char* model, char* partno, char* version); //changed in v 3.0
extern int _stdcall HH_GetSerialNumber(int devidx, char* serial);
extern int _stdcall HH_GetFeatures(int devidx, int* features);                                //new in v 3.0
extern int _stdcall HH_GetBaseResolution(int devidx, double* resolution, int* binsteps);
extern int _stdcall HH_GetHardwareDebugInfo(int devidx, char *debuginfo);                     //new in v 3.0

extern int _stdcall HH_GetNumOfInputChannels(int devidx, int* nchannels);
extern int _stdcall HH_GetNumOfModules(int devidx, int* nummod);
extern int _stdcall HH_GetModuleInfo(int devidx, int modidx, int* modelcode, int* versioncode);
extern int _stdcall HH_GetModuleIndex(int devidx, int channel, int* modidx);

extern int _stdcall HH_Calibrate(int devidx);

extern int _stdcall HH_SetSyncDiv(int devidx, int div);
extern int _stdcall HH_SetSyncCFD(int devidx, int level, int zc);
extern int _stdcall HH_SetSyncChannelOffset(int devidx, int value);

extern int _stdcall HH_SetInputCFD(int devidx, int channel, int level, int zc);
extern int _stdcall HH_SetInputChannelOffset(int devidx, int channel, int value);
extern int _stdcall HH_SetInputChannelEnable(int devidx, int channel, int enable);

extern int _stdcall HH_SetStopOverflow(int devidx, int stop_ovfl, unsigned int stopcount);	
extern int _stdcall HH_SetBinning(int devidx, int binning);
extern int _stdcall HH_SetOffset(int devidx, int offset);
extern int _stdcall HH_SetHistoLen(int devidx, int lencode, int* actuallen); 
extern int _stdcall HH_SetMeasControl(int devidx, int control, int startedge, int stopedge);

extern int _stdcall HH_ClearHistMem(int devidx);
extern int _stdcall HH_StartMeas(int devidx, int tacq);
extern int _stdcall HH_StopMeas(int devidx);
extern int _stdcall HH_CTCStatus(int devidx, int* ctcstatus);

extern int _stdcall HH_GetHistogram(int devidx, unsigned int *chcount, int channel, int clear);
extern int _stdcall HH_GetResolution(int devidx, double* resolution); 
extern int _stdcall HH_GetSyncPeriod(int devidx, double* period);                             //new in v 3.0
extern int _stdcall HH_GetSyncRate(int devidx, int* syncrate);
extern int _stdcall HH_GetCountRate(int devidx, int channel, int* cntrate);
extern int _stdcall HH_GetFlags(int devidx, int* flags);
extern int _stdcall HH_GetElapsedMeasTime(int devidx, double* elapsed);

extern int _stdcall HH_GetWarnings(int devidx, int* warnings);
extern int _stdcall HH_GetWarningsText(int devidx, char* text, int warnings);


//for TT modes
extern int _stdcall HH_SetMarkerHoldoffTime(int devidx, int holdofftime);                     //new in v 3.0
extern int _stdcall HH_SetMarkerEdges(int devidx, int me1, int me2, int me3, int me4);
extern int _stdcall HH_SetMarkerEnable(int devidx, int en1, int en2, int en3, int en4);
extern int _stdcall HH_ReadFiFo(int devidx, unsigned int* buffer, int count, int* nactual);

//for Continuous mode
extern int _stdcall HH_GetContModeBlock(int devidx, void* buffer, int* nbytesreceived);



