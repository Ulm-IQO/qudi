:: Basically this just creates a VBS Script on the fly and invokes the batch
:: script using it.  It checks to see if the current window is running as
:: administrator by attempting to create a folder that requires administrative
:: access.  If the directory can not be created, then it invokes the UAC
:: dialog, then closes the non-admin window.  The script can also be executed
:: from an already open administrative CLI.

:: Idea is taken from:
:: https://sites.google.com/site/eneerge/scripts/batchgotadmin

@echo off

:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"
:--------------------------------------



pip install fysom
pip install pyqtgraph
pip install pyvisa
pip install pydaqmx
pip install svn
pip install lmfit
pip install rpyc
pause
