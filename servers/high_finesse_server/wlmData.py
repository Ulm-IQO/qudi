######################################################################################################
# @package wlmData
# @file wlmData.py
# @copyright HighFinesse GmbH.
# @date 2020.06.02
# @version 0.4
#
# Homepage: http://www.highfinesse.com/
#
# @brief Python wrapper for wlmData.dll.
#
# Changelog:
# ----------
# 2018.09.12
# v0.1 - Initial release
# 2018.09.14
# v0.2 - Constant values added
# 2018.09.15
# v0.3 - Constant values separated to wlmConst.py, LoadDLL() added
# 2020.06.02
# v0.4 - GetPattern... and GetAnalysisData argtypes adapted
#/

import ctypes

dll = None

def LoadDLL(DLL_Path):
    global dll
    dll = ctypes.WinDLL(DLL_Path)

    # LONG_PTR Instantiate(long RFC, long Mode, LONG_PTR P1, long P2)
    dll.Instantiate.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_long ]
    dll.Instantiate.restype = ctypes.POINTER(ctypes.c_long)

    # long WaitForWLMEvent(lref Mode, lref IntVal, dref DblVal)
    dll.WaitForWLMEvent.argtypes = [ ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double) ]
    dll.WaitForWLMEvent.restype = ctypes.c_long

    # long WaitForWLMEventEx(lref Ver, lref Mode, lref IntVal, dref DblVal, lref Res1)
    dll.WaitForWLMEventEx.argtypes = [ ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_long) ]
    dll.WaitForWLMEventEx.restype = ctypes.c_long

    # long WaitForNextWLMEvent(lref Mode, lref IntVal, dref DblVal)
    dll.WaitForNextWLMEvent.argtypes = [ ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double) ]
    dll.WaitForNextWLMEvent.restype = ctypes.c_long

    # long WaitForNextWLMEventEx(lref Ver, lref Mode, lref IntVal, dref DblVal, lref Res1)
    dll.WaitForNextWLMEventEx.argtypes = [ ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_long) ]
    dll.WaitForNextWLMEventEx.restype = ctypes.c_long

    # void ClearWLMEvents(void)
    dll.ClearWLMEvents.argtypes = [  ]
    dll.ClearWLMEvents.restype = None

    # long ControlWLM(long Action, LONG_PTR App, long Ver)
    dll.ControlWLM.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_long ]
    dll.ControlWLM.restype = ctypes.c_long

    # long ControlWLMEx(long Action, LONG_PTR App, long Ver, long Delay, long Res)
    dll.ControlWLMEx.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.ControlWLMEx.restype = ctypes.c_long

    # __int64 SynchroniseWLM(long Mode, __int64 TS)
    dll.SynchroniseWLM.argtypes = [ ctypes.c_long, ctypes.c_longlong ]
    dll.SynchroniseWLM.restype = ctypes.c_longlong

    # long SetMeasurementDelayMethod(long Mode, long Delay)
    dll.SetMeasurementDelayMethod.argtypes = [ ctypes.c_long, ctypes.c_long ]
    dll.SetMeasurementDelayMethod.restype = ctypes.c_long

    # long SetWLMPriority(long PPC, long Res1, long Res2)
    dll.SetWLMPriority.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetWLMPriority.restype = ctypes.c_long

    # long PresetWLMIndex(long Ver)
    dll.PresetWLMIndex.argtypes = [ ctypes.c_long ]
    dll.PresetWLMIndex.restype = ctypes.c_long

    # long GetWLMVersion(long Ver)
    dll.GetWLMVersion.argtypes = [ ctypes.c_long ]
    dll.GetWLMVersion.restype = ctypes.c_long

    # long GetWLMIndex(long Ver)
    dll.GetWLMIndex.argtypes = [ ctypes.c_long ]
    dll.GetWLMIndex.restype = ctypes.c_long

    # long GetWLMCount(long V)
    dll.GetWLMCount.argtypes = [ ctypes.c_long ]
    dll.GetWLMCount.restype = ctypes.c_long

    # double GetWavelength(double WL)
    dll.GetWavelength.argtypes = [ ctypes.c_double ]
    dll.GetWavelength.restype = ctypes.c_double

    # double GetWavelength2(double WL2)
    dll.GetWavelength2.argtypes = [ ctypes.c_double ]
    dll.GetWavelength2.restype = ctypes.c_double

    # double GetWavelengthNum(long num, double WL)
    dll.GetWavelengthNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetWavelengthNum.restype = ctypes.c_double

    # double GetCalWavelength(long ba, double WL)
    dll.GetCalWavelength.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetCalWavelength.restype = ctypes.c_double

    # double GetCalibrationEffect(double CE)
    dll.GetCalibrationEffect.argtypes = [ ctypes.c_double ]
    dll.GetCalibrationEffect.restype = ctypes.c_double

    # double GetFrequency(double F)
    dll.GetFrequency.argtypes = [ ctypes.c_double ]
    dll.GetFrequency.restype = ctypes.c_double

    # double GetFrequency2(double F2)
    dll.GetFrequency2.argtypes = [ ctypes.c_double ]
    dll.GetFrequency2.restype = ctypes.c_double

    # double GetFrequencyNum(long num, double F)
    dll.GetFrequencyNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetFrequencyNum.restype = ctypes.c_double

    # double GetLinewidth(long Index, double LW)
    dll.GetLinewidth.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetLinewidth.restype = ctypes.c_double

    # double GetLinewidthNum(long num, double LW)
    dll.GetLinewidthNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetLinewidthNum.restype = ctypes.c_double

    # double GetDistance(double D)
    dll.GetDistance.argtypes = [ ctypes.c_double ]
    dll.GetDistance.restype = ctypes.c_double

    # double GetAnalogIn(double AI)
    dll.GetAnalogIn.argtypes = [ ctypes.c_double ]
    dll.GetAnalogIn.restype = ctypes.c_double

    # double GetTemperature(double T)
    dll.GetTemperature.argtypes = [ ctypes.c_double ]
    dll.GetTemperature.restype = ctypes.c_double

    # long SetTemperature(double T)
    dll.SetTemperature.argtypes = [ ctypes.c_double ]
    dll.SetTemperature.restype = ctypes.c_long

    # double GetPressure(double P)
    dll.GetPressure.argtypes = [ ctypes.c_double ]
    dll.GetPressure.restype = ctypes.c_double

    # long SetPressure(long Mode, double P)
    dll.SetPressure.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.SetPressure.restype = ctypes.c_long

    # double GetExternalInput(long Index, double I)
    dll.GetExternalInput.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetExternalInput.restype = ctypes.c_double

    # long SetExternalInput(long Index, double I)
    dll.SetExternalInput.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.SetExternalInput.restype = ctypes.c_long

    # long GetExtraSetting(long Index, lref lGet, dref dGet, sref sGet)
    dll.GetExtraSetting.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double), ctypes.c_char_p ]
    dll.GetExtraSetting.restype = ctypes.c_long

    # long SetExtraSetting(long Index, long lSet, double dSet, sref sSet)
    dll.SetExtraSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_double, ctypes.c_char_p ]
    dll.SetExtraSetting.restype = ctypes.c_long

    # unsigned short GetExposure(unsigned short E)
    dll.GetExposure.argtypes = [ ctypes.c_ushort ]
    dll.GetExposure.restype = ctypes.c_ushort

    # long SetExposure(unsigned short E)
    dll.SetExposure.argtypes = [ ctypes.c_ushort ]
    dll.SetExposure.restype = ctypes.c_long

    # unsigned short GetExposure2(unsigned short E2)
    dll.GetExposure2.argtypes = [ ctypes.c_ushort ]
    dll.GetExposure2.restype = ctypes.c_ushort

    # long SetExposure2(unsigned short E2)
    dll.SetExposure2.argtypes = [ ctypes.c_ushort ]
    dll.SetExposure2.restype = ctypes.c_long

    # long GetExposureNum(long num, long arr, long E)
    dll.GetExposureNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.GetExposureNum.restype = ctypes.c_long

    # long SetExposureNum(long num, long arr, long E)
    dll.SetExposureNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetExposureNum.restype = ctypes.c_long

    # double GetExposureNumEx(long num, long arr, double E)
    dll.GetExposureNumEx.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_double ]
    dll.GetExposureNumEx.restype = ctypes.c_double

    # long SetExposureNumEx(long num, long arr, double E)
    dll.SetExposureNumEx.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_double ]
    dll.SetExposureNumEx.restype = ctypes.c_long

    # bool GetExposureMode(bool EM)
    dll.GetExposureMode.argtypes = [ ctypes.c_bool ]
    dll.GetExposureMode.restype = ctypes.c_bool

    # long SetExposureMode(bool EM)
    dll.SetExposureMode.argtypes = [ ctypes.c_bool ]
    dll.SetExposureMode.restype = ctypes.c_long

    # long GetExposureModeNum(long num, bool EM)
    dll.GetExposureModeNum.argtypes = [ ctypes.c_long, ctypes.c_bool ]
    dll.GetExposureModeNum.restype = ctypes.c_long

    # long SetExposureModeNum(long num, bool EM)
    dll.SetExposureModeNum.argtypes = [ ctypes.c_long, ctypes.c_bool ]
    dll.SetExposureModeNum.restype = ctypes.c_long

    # long GetExposureRange(long ER)
    dll.GetExposureRange.argtypes = [ ctypes.c_long ]
    dll.GetExposureRange.restype = ctypes.c_long

    # long GetAutoExposureSetting(long num, long AES, lref iVal, dref dVal)
    dll.GetAutoExposureSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double) ]
    dll.GetAutoExposureSetting.restype = ctypes.c_long

    # long SetAutoExposureSetting(long num, long AES, long iVal, double dVal)
    dll.SetAutoExposureSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_double ]
    dll.SetAutoExposureSetting.restype = ctypes.c_long

    # unsigned short GetResultMode(unsigned short RM)
    dll.GetResultMode.argtypes = [ ctypes.c_ushort ]
    dll.GetResultMode.restype = ctypes.c_ushort

    # long SetResultMode(unsigned short RM)
    dll.SetResultMode.argtypes = [ ctypes.c_ushort ]
    dll.SetResultMode.restype = ctypes.c_long

    # unsigned short GetRange(unsigned short R)
    dll.GetRange.argtypes = [ ctypes.c_ushort ]
    dll.GetRange.restype = ctypes.c_ushort

    # long SetRange(unsigned short R)
    dll.SetRange.argtypes = [ ctypes.c_ushort ]
    dll.SetRange.restype = ctypes.c_long

    # unsigned short GetPulseMode(unsigned short PM)
    dll.GetPulseMode.argtypes = [ ctypes.c_ushort ]
    dll.GetPulseMode.restype = ctypes.c_ushort

    # long SetPulseMode(unsigned short PM)
    dll.SetPulseMode.argtypes = [ ctypes.c_ushort ]
    dll.SetPulseMode.restype = ctypes.c_long

    # long GetPulseDelay(long PD)
    dll.GetPulseDelay.argtypes = [ ctypes.c_long ]
    dll.GetPulseDelay.restype = ctypes.c_long

    # long SetPulseDelay(long PD)
    dll.SetPulseDelay.argtypes = [ ctypes.c_long ]
    dll.SetPulseDelay.restype = ctypes.c_long

    # unsigned short GetWideMode(unsigned short WM)
    dll.GetWideMode.argtypes = [ ctypes.c_ushort ]
    dll.GetWideMode.restype = ctypes.c_ushort

    # long SetWideMode(unsigned short WM)
    dll.SetWideMode.argtypes = [ ctypes.c_ushort ]
    dll.SetWideMode.restype = ctypes.c_long

    # long GetDisplayMode(long DM)
    dll.GetDisplayMode.argtypes = [ ctypes.c_long ]
    dll.GetDisplayMode.restype = ctypes.c_long

    # long SetDisplayMode(long DM)
    dll.SetDisplayMode.argtypes = [ ctypes.c_long ]
    dll.SetDisplayMode.restype = ctypes.c_long

    # bool GetFastMode(bool FM)
    dll.GetFastMode.argtypes = [ ctypes.c_bool ]
    dll.GetFastMode.restype = ctypes.c_bool

    # long SetFastMode(bool FM)
    dll.SetFastMode.argtypes = [ ctypes.c_bool ]
    dll.SetFastMode.restype = ctypes.c_long

    # bool GetLinewidthMode(bool LM)
    dll.GetLinewidthMode.argtypes = [ ctypes.c_bool ]
    dll.GetLinewidthMode.restype = ctypes.c_bool

    # long SetLinewidthMode(bool LM)
    dll.SetLinewidthMode.argtypes = [ ctypes.c_bool ]
    dll.SetLinewidthMode.restype = ctypes.c_long

    # bool GetDistanceMode(bool DM)
    dll.GetDistanceMode.argtypes = [ ctypes.c_bool ]
    dll.GetDistanceMode.restype = ctypes.c_bool

    # long SetDistanceMode(bool DM)
    dll.SetDistanceMode.argtypes = [ ctypes.c_bool ]
    dll.SetDistanceMode.restype = ctypes.c_long

    # long GetSwitcherMode(long SM)
    dll.GetSwitcherMode.argtypes = [ ctypes.c_long ]
    dll.GetSwitcherMode.restype = ctypes.c_long

    # long SetSwitcherMode(long SM)
    dll.SetSwitcherMode.argtypes = [ ctypes.c_long ]
    dll.SetSwitcherMode.restype = ctypes.c_long

    # long GetSwitcherChannel(long CH)
    dll.GetSwitcherChannel.argtypes = [ ctypes.c_long ]
    dll.GetSwitcherChannel.restype = ctypes.c_long

    # long SetSwitcherChannel(long CH)
    dll.SetSwitcherChannel.argtypes = [ ctypes.c_long ]
    dll.SetSwitcherChannel.restype = ctypes.c_long

    # long GetSwitcherSignalStates(long Signal, lref Use, lref Show)
    dll.GetSwitcherSignalStates.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long) ]
    dll.GetSwitcherSignalStates.restype = ctypes.c_long

    # long SetSwitcherSignalStates(long Signal, long Use, long Show)
    dll.SetSwitcherSignalStates.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetSwitcherSignalStates.restype = ctypes.c_long

    # long SetSwitcherSignal(long Signal, long Use, long Show)
    dll.SetSwitcherSignal.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetSwitcherSignal.restype = ctypes.c_long

    # long GetAutoCalMode(long ACM)
    dll.GetAutoCalMode.argtypes = [ ctypes.c_long ]
    dll.GetAutoCalMode.restype = ctypes.c_long

    # long SetAutoCalMode(long ACM)
    dll.SetAutoCalMode.argtypes = [ ctypes.c_long ]
    dll.SetAutoCalMode.restype = ctypes.c_long

    # long GetAutoCalSetting(long ACS, lref val, long Res1, lref Res2)
    dll.GetAutoCalSetting.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_long, ctypes.POINTER(ctypes.c_long) ]
    dll.GetAutoCalSetting.restype = ctypes.c_long

    # long SetAutoCalSetting(long ACS, long val, long Res1, long Res2)
    dll.SetAutoCalSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetAutoCalSetting.restype = ctypes.c_long

    # long GetActiveChannel(long Mode, lref Port, long Res1)
    dll.GetActiveChannel.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.c_long ]
    dll.GetActiveChannel.restype = ctypes.c_long

    # long SetActiveChannel(long Mode, long Port, long CH, long Res1)
    dll.SetActiveChannel.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetActiveChannel.restype = ctypes.c_long

    # long GetChannelsCount(long C)
    dll.GetChannelsCount.argtypes = [ ctypes.c_long ]
    dll.GetChannelsCount.restype = ctypes.c_long

    # unsigned short GetOperationState(unsigned short OS)
    dll.GetOperationState.argtypes = [ ctypes.c_ushort ]
    dll.GetOperationState.restype = ctypes.c_ushort

    # long Operation(unsigned short Op)
    dll.Operation.argtypes = [ ctypes.c_ushort ]
    dll.Operation.restype = ctypes.c_long

    # long SetOperationFile(sref lpFile)
    dll.SetOperationFile.argtypes = [ ctypes.c_char_p ]
    dll.SetOperationFile.restype = ctypes.c_long

    # long Calibration(long Type, long Unit, double Value, long Channel)
    dll.Calibration.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_double, ctypes.c_long ]
    dll.Calibration.restype = ctypes.c_long

    # long RaiseMeasurementEvent(long Mode)
    dll.RaiseMeasurementEvent.argtypes = [ ctypes.c_long ]
    dll.RaiseMeasurementEvent.restype = ctypes.c_long

    # long TriggerMeasurement(long Action)
    dll.TriggerMeasurement.argtypes = [ ctypes.c_long ]
    dll.TriggerMeasurement.restype = ctypes.c_long

    # long GetTriggerState(long TS)
    dll.GetTriggerState.argtypes = [ ctypes.c_long ]
    dll.GetTriggerState.restype = ctypes.c_long

    # long GetInterval(long I)
    dll.GetInterval.argtypes = [ ctypes.c_long ]
    dll.GetInterval.restype = ctypes.c_long

    # long SetInterval(long I)
    dll.SetInterval.argtypes = [ ctypes.c_long ]
    dll.SetInterval.restype = ctypes.c_long

    # bool GetIntervalMode(bool IM)
    dll.GetIntervalMode.argtypes = [ ctypes.c_bool ]
    dll.GetIntervalMode.restype = ctypes.c_bool

    # long SetIntervalMode(bool IM)
    dll.SetIntervalMode.argtypes = [ ctypes.c_bool ]
    dll.SetIntervalMode.restype = ctypes.c_long

    # long GetBackground(long BG)
    dll.GetBackground.argtypes = [ ctypes.c_long ]
    dll.GetBackground.restype = ctypes.c_long

    # long SetBackground(long BG)
    dll.SetBackground.argtypes = [ ctypes.c_long ]
    dll.SetBackground.restype = ctypes.c_long

    # long GetAveragingSettingNum(long num, long AS, long Value)
    dll.GetAveragingSettingNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.GetAveragingSettingNum.restype = ctypes.c_long

    # long SetAveragingSettingNum(long num, long AS, long Value)
    dll.SetAveragingSettingNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.SetAveragingSettingNum.restype = ctypes.c_long

    # bool GetLinkState(bool LS)
    dll.GetLinkState.argtypes = [ ctypes.c_bool ]
    dll.GetLinkState.restype = ctypes.c_bool

    # long SetLinkState(bool LS)
    dll.SetLinkState.argtypes = [ ctypes.c_bool ]
    dll.SetLinkState.restype = ctypes.c_long

    # void LinkSettingsDlg(void)
    dll.LinkSettingsDlg.argtypes = [  ]
    dll.LinkSettingsDlg.restype = None

    # long GetPatternItemSize(long Index)
    dll.GetPatternItemSize.argtypes = [ ctypes.c_long ]
    dll.GetPatternItemSize.restype = ctypes.c_long

    # long GetPatternItemCount(long Index)
    dll.GetPatternItemCount.argtypes = [ ctypes.c_long ]
    dll.GetPatternItemCount.restype = ctypes.c_long

    # ULONG_PTR GetPattern(long Index)
    dll.GetPattern.argtypes = [ ctypes.c_long ]
    dll.GetPattern.restype = ctypes.POINTER(ctypes.c_ulong)

    # ULONG_PTR GetPatternNum(long Chn, long Index)
    dll.GetPatternNum.argtypes = [ ctypes.c_long, ctypes.c_long ]
    dll.GetPatternNum.restype = ctypes.POINTER(ctypes.c_ulong)

    # long GetPatternData(long Index, ULONG_PTR PArray)
    dll.GetPatternData.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_short) ]
    dll.GetPatternData.restype = ctypes.c_long

    # long GetPatternDataNum(long Chn, long Index, ULONG_PTR PArray)
    dll.GetPatternDataNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_short) ]
    dll.GetPatternDataNum.restype = ctypes.c_long

    # long SetPattern(long Index, long iEnable)
    dll.SetPattern.argtypes = [ ctypes.c_long, ctypes.c_long ]
    dll.SetPattern.restype = ctypes.c_long

    # long SetPatternData(long Index, ULONG_PTR PArray)
    dll.SetPatternData.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_ulong) ]
    dll.SetPatternData.restype = ctypes.c_long

    # bool GetAnalysisMode(bool AM)
    dll.GetAnalysisMode.argtypes = [ ctypes.c_bool ]
    dll.GetAnalysisMode.restype = ctypes.c_bool

    # long SetAnalysisMode(bool AM)
    dll.SetAnalysisMode.argtypes = [ ctypes.c_bool ]
    dll.SetAnalysisMode.restype = ctypes.c_long

    # long GetAnalysisItemSize(long Index)
    dll.GetAnalysisItemSize.argtypes = [ ctypes.c_long ]
    dll.GetAnalysisItemSize.restype = ctypes.c_long

    # long GetAnalysisItemCount(long Index)
    dll.GetAnalysisItemCount.argtypes = [ ctypes.c_long ]
    dll.GetAnalysisItemCount.restype = ctypes.c_long

    # ULONG_PTR GetAnalysis(long Index)
    dll.GetAnalysis.argtypes = [ ctypes.c_long ]
    dll.GetAnalysis.restype = ctypes.POINTER(ctypes.c_ulong)

    # long GetAnalysisData(long Index, ULONG_PTR PArray)
    dll.GetAnalysisData.argtypes = [ ctypes.c_long, ctypes.POINTER(ctypes.c_double) ]
    dll.GetAnalysisData.restype = ctypes.c_long

    # long SetAnalysis(long Index, long iEnable)
    dll.SetAnalysis.argtypes = [ ctypes.c_long, ctypes.c_long ]
    dll.SetAnalysis.restype = ctypes.c_long

    # long GetMinPeak(long M1)
    dll.GetMinPeak.argtypes = [ ctypes.c_long ]
    dll.GetMinPeak.restype = ctypes.c_long

    # long GetMinPeak2(long M2)
    dll.GetMinPeak2.argtypes = [ ctypes.c_long ]
    dll.GetMinPeak2.restype = ctypes.c_long

    # long GetMaxPeak(long X1)
    dll.GetMaxPeak.argtypes = [ ctypes.c_long ]
    dll.GetMaxPeak.restype = ctypes.c_long

    # long GetMaxPeak2(long X2)
    dll.GetMaxPeak2.argtypes = [ ctypes.c_long ]
    dll.GetMaxPeak2.restype = ctypes.c_long

    # long GetAvgPeak(long A1)
    dll.GetAvgPeak.argtypes = [ ctypes.c_long ]
    dll.GetAvgPeak.restype = ctypes.c_long

    # long GetAvgPeak2(long A2)
    dll.GetAvgPeak2.argtypes = [ ctypes.c_long ]
    dll.GetAvgPeak2.restype = ctypes.c_long

    # long SetAvgPeak(long PA)
    dll.SetAvgPeak.argtypes = [ ctypes.c_long ]
    dll.SetAvgPeak.restype = ctypes.c_long

    # long GetAmplitudeNum(long num, long Index, long A)
    dll.GetAmplitudeNum.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.GetAmplitudeNum.restype = ctypes.c_long

    # double GetIntensityNum(long num, double I)
    dll.GetIntensityNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetIntensityNum.restype = ctypes.c_double

    # double GetPowerNum(long num, double P)
    dll.GetPowerNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetPowerNum.restype = ctypes.c_double

    # unsigned short GetDelay(unsigned short D)
    dll.GetDelay.argtypes = [ ctypes.c_ushort ]
    dll.GetDelay.restype = ctypes.c_ushort

    # long SetDelay(unsigned short D)
    dll.SetDelay.argtypes = [ ctypes.c_ushort ]
    dll.SetDelay.restype = ctypes.c_long

    # unsigned short GetShift(unsigned short S)
    dll.GetShift.argtypes = [ ctypes.c_ushort ]
    dll.GetShift.restype = ctypes.c_ushort

    # long SetShift(unsigned short S)
    dll.SetShift.argtypes = [ ctypes.c_ushort ]
    dll.SetShift.restype = ctypes.c_long

    # unsigned short GetShift2(unsigned short S2)
    dll.GetShift2.argtypes = [ ctypes.c_ushort ]
    dll.GetShift2.restype = ctypes.c_ushort

    # long SetShift2(unsigned short S2)
    dll.SetShift2.argtypes = [ ctypes.c_ushort ]
    dll.SetShift2.restype = ctypes.c_long

    # bool GetDeviationMode(bool DM)
    dll.GetDeviationMode.argtypes = [ ctypes.c_bool ]
    dll.GetDeviationMode.restype = ctypes.c_bool

    # long SetDeviationMode(bool DM)
    dll.SetDeviationMode.argtypes = [ ctypes.c_bool ]
    dll.SetDeviationMode.restype = ctypes.c_long

    # double GetDeviationReference(double DR)
    dll.GetDeviationReference.argtypes = [ ctypes.c_double ]
    dll.GetDeviationReference.restype = ctypes.c_double

    # long SetDeviationReference(double DR)
    dll.SetDeviationReference.argtypes = [ ctypes.c_double ]
    dll.SetDeviationReference.restype = ctypes.c_long

    # long GetDeviationSensitivity(long DS)
    dll.GetDeviationSensitivity.argtypes = [ ctypes.c_long ]
    dll.GetDeviationSensitivity.restype = ctypes.c_long

    # long SetDeviationSensitivity(long DS)
    dll.SetDeviationSensitivity.argtypes = [ ctypes.c_long ]
    dll.SetDeviationSensitivity.restype = ctypes.c_long

    # double GetDeviationSignal(double DS)
    dll.GetDeviationSignal.argtypes = [ ctypes.c_double ]
    dll.GetDeviationSignal.restype = ctypes.c_double

    # double GetDeviationSignalNum(long Port, double DS)
    dll.GetDeviationSignalNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.GetDeviationSignalNum.restype = ctypes.c_double

    # long SetDeviationSignal(double DS)
    dll.SetDeviationSignal.argtypes = [ ctypes.c_double ]
    dll.SetDeviationSignal.restype = ctypes.c_long

    # long SetDeviationSignalNum(long Port, double DS)
    dll.SetDeviationSignalNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.SetDeviationSignalNum.restype = ctypes.c_long

    # double RaiseDeviationSignal(long iType, double dSignal)
    dll.RaiseDeviationSignal.argtypes = [ ctypes.c_long, ctypes.c_double ]
    dll.RaiseDeviationSignal.restype = ctypes.c_double

    # long GetPIDCourse(sref PIDC)
    dll.GetPIDCourse.argtypes = [ ctypes.c_char_p ]
    dll.GetPIDCourse.restype = ctypes.c_long

    # long SetPIDCourse(sref PIDC)
    dll.SetPIDCourse.argtypes = [ ctypes.c_char_p ]
    dll.SetPIDCourse.restype = ctypes.c_long

    # long GetPIDCourseNum(long Port, sref PIDC)
    dll.GetPIDCourseNum.argtypes = [ ctypes.c_long, ctypes.c_char_p ]
    dll.GetPIDCourseNum.restype = ctypes.c_long

    # long SetPIDCourseNum(long Port, sref PIDC)
    dll.SetPIDCourseNum.argtypes = [ ctypes.c_long, ctypes.c_char_p ]
    dll.SetPIDCourseNum.restype = ctypes.c_long

    # long GetPIDSetting(long PS, long Port, lref iSet, dref dSet)
    dll.GetPIDSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double) ]
    dll.GetPIDSetting.restype = ctypes.c_long

    # long SetPIDSetting(long PS, long Port, long iSet, double dSet)
    dll.SetPIDSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_double ]
    dll.SetPIDSetting.restype = ctypes.c_long

    # long GetLaserControlSetting(long PS, long Port, lref iSet, dref dSet, sref sSet)
    dll.GetLaserControlSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_double), ctypes.c_char_p ]
    dll.GetLaserControlSetting.restype = ctypes.c_long

    # long SetLaserControlSetting(long PS, long Port, long iSet, double dSet, sref sSet)
    dll.SetLaserControlSetting.argtypes = [ ctypes.c_long, ctypes.c_long, ctypes.c_long, ctypes.c_double, ctypes.c_char_p ]
    dll.SetLaserControlSetting.restype = ctypes.c_long

    # long ClearPIDHistory(long Port)
    dll.ClearPIDHistory.argtypes = [ ctypes.c_long ]
    dll.ClearPIDHistory.restype = ctypes.c_long

    # double ConvertUnit(double Val, long uFrom, long uTo)
    dll.ConvertUnit.argtypes = [ ctypes.c_double, ctypes.c_long, ctypes.c_long ]
    dll.ConvertUnit.restype = ctypes.c_double

    # double ConvertDeltaUnit(double Base, double Delta, long uBase, long uFrom, long uTo)
    dll.ConvertDeltaUnit.argtypes = [ ctypes.c_double, ctypes.c_double, ctypes.c_long, ctypes.c_long, ctypes.c_long ]
    dll.ConvertDeltaUnit.restype = ctypes.c_double

    # bool GetReduced(bool R)
    dll.GetReduced.argtypes = [ ctypes.c_bool ]
    dll.GetReduced.restype = ctypes.c_bool

    # long SetReduced(bool R)
    dll.SetReduced.argtypes = [ ctypes.c_bool ]
    dll.SetReduced.restype = ctypes.c_long

    # unsigned short GetScale(unsigned short S)
    dll.GetScale.argtypes = [ ctypes.c_ushort ]
    dll.GetScale.restype = ctypes.c_ushort

    # long SetScale(unsigned short S)
    dll.SetScale.argtypes = [ ctypes.c_ushort ]
    dll.SetScale.restype = ctypes.c_long

