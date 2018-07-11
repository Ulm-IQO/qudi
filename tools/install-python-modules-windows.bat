::
:: This file contains the bat script for windows to install the needed python modules
::
:: Qudi is free software: you can redistribute it and/or modify
:: it under the terms of the GNU General Public License as published by
:: the Free Software Foundation, either version 3 of the License, or
:: (at your option) any later version.
::
:: Qudi is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
:: GNU General Public License for more details.
::
:: You should have received a copy of the GNU General Public License
:: along with Qudi. If not, see <http://www.gnu.org/licenses/>.
::
:: Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de


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
:: -------------------------------------
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
REM --------------------------------------

REM Run locally a powershell script to be able to catch the interrupt from the 
REM exception if an environment is not present.

powershell.exe "Try {conda env remove --yes --name qudi} Catch {return 'No conda environment with name <qudi> is present'}" 

echo Initiating installation of conda environment with name 'qudi'...

REM Get the processor architecture, 32bit or 64bit
reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT

REM Get the windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j

REM Get which environment to install for a specific windows version.

if "%version%" == "6.1" (
    if %OS% == 32BIT ( 
        echo Detected: Windows 7, 32bit 
        powershell.exe "conda env create -f '%~dp0\conda-env-win7-32bit-qt5.yml' "
    ) else ( 
        echo Detected: Windows 7, 64bit 
        powershell.exe "conda env create -f '%~dp0\conda-env-win7-64bit-qt5.yml' "
    ) 
)
        
if "%version%" == "6.2" (
    echo Detected: Windows 8, %OS%
        powershell.exe "conda env create -f '%~dp0\conda-env-win8-qt5.yml' "
    )

if "%version%" == "6.3" (
    echo Detected: Windows 8.1, %OS%
        powershell.exe "conda env create -f '%~dp0\conda-env-win8-qt5.yml' "
    )

if "%version%" == "10.0" (
    echo Detected: Windows 10, %OS%
        powershell.exe "conda env create -f '%~dp0\conda-env-win10-64bit-qt5.yml' "
    )


echo Installation procedure for conda environment 'qudi' finished.
pause