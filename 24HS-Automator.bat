@echo off
title 24HS Automator
set version=1.0.0
setlocal EnableDelayedExpansion

REM Some stuff here might need changing every once in a while (sorted from most to least likely to change)
set latestWindowsVersion=20H2
set updateAssistantURL=https://download.microsoft.com/download/2/b/b/2bba292a-21c3-42a6-8123-98265faff0b6/Windows10Upgrade9252.exe
set manjaroURL=https://osdn.net/dl/manjaro/manjaro-kde-20.2.1-minimal-210103-linux59.iso
set legacyBIOSURL=https://www.reddit.com/r/24hoursupport/wiki/enteringbios#wiki_cannot_boot_into_system_or_legacy_.28non_uefi.29_board
set hirensURL=https://www.hirensbootcd.org/files/HBCD_PE_x64.iso
set memtestURL=https://www.memtest86.com/downloads/memtest86-usb.zip
set file2clipURL=https://github.com/rostok/file2clip/raw/master/file2clip.exe

REM Go into the script's location (change drive letter, cd into directory)
REM This is only necessary because we're (usually) running the script as administrator
%~d0
cd %~dp0

REM Check if the script was ran with administrative permissions. If not, run it with them
call :checkPermissions

REM Check if we're currently running in safe mode (to either display "Enter"- or "Exit safe boot")
call :checkSafeMode

:menu
cls
echo 24HS Automator v%version%
echo What do you want to do?
echo (1) Check system files
echo (2) Check update status
echo (3) Flash ISOs (Hirens/Memtest/Linux)
if %inSafeMode% EQU 0 (
	echo ^(4^) Enter safe mode
) else echo ^(4^) Exit safe mode
echo (5) Perform clean boot
echo (6) Generate system info
echo (7) Enter BIOS
choice /c 1234567 /N
echo.
if %ERRORLEVEL% EQU 1 (
	call :checkFiles
) else if %ERRORLEVEL% EQU 2 (
	call :systemUpToDate
) else if %ERRORLEVEL% EQU 3 (
	call :isoFlash
) else if %ERRORLEVEL% EQU 4 (
	if %inSafeMode% EQU 0 (
	call :enterSafeMode
	) else call :exitSafeMode
) else if %ERRORLEVEL% EQU 5 (
	call :cleanBoot
) else if %ERRORLEVEL% EQU 6 (
	call :sysinfo
) else if %ERRORLEVEL% EQU 7 (
	call :enterBIOS
)
goto menu


:checkFiles
echo Running SFC and DISM scans...
sfc /scannow
echo.
echo SFC scan completed, running DISM next
pause
dism /Online /Cleanup-Image /RestoreHealth
echo DISM completed. Reboot now?
choice
REM /soft = Wait for programs to quit
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:systemUpToDate
REM Gets the display name out of the registry
>nul for /F "tokens=3 skip=2" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "DisplayVersion"') do set currentVersion=%%a
if %ERRORLEVEL% NEQ 0 set currentVersion=1903
REM Compare that to the set value
if %currentVersion% EQU %latestWindowsVersion% (
	echo Major Windows version is up to date^^!
	echo Opening Settings and searching for minor updates there...
	REM Open up the Settings' Update tab
	control update
	REM Kick off the Update Session Orchestrator to start searching for updates
	REM All switches for that tool are listed at https://www.urtech.ca/2018/11/usoclient-documentation-switches/
	usoclient StartInteractiveScan
	echo Also checking for GPU driver updates...
	
) else (
	echo You're not on the latest version^^! Downloading and launching update assistant...
	REM --location = follow redirects
	if not exist %TEMP%\updateAssistant.exe curl %updateAssistantURL% --silent --location --output %TEMP%\updateAssistant.exe
	%TEMP%\updateAssistant.exe
)
echo Press any key to return to the main menu...
>nul pause
exit /b 0


:isoFlash
exit /b 0


:enterSafeMode
echo Which type of safe mode do you want to enter?
echo (D) Default
echo (N) With networking
echo (C) With command prompt
for /f "skip=3" %%a in ('powershell -Command "Get-LocalUser | Where-Object { $_.Enabled -match \"True\"} | Select-Object PrincipalSource"') do set accType=%%a
if %accType% EQU MicrosoftAccount (
	echo.
	echo Warning: Your user account is not a local account.
	echo You will not be able to login when choosing anything other than "With networking"^^!
)
choice /c DNC /n
REM Not sure if bcdedit sets ERRORLEVEL, store it to be safe
set tmpERRORLEVEL=%ERRORLEVEL%
if %tmpERRORLEVEL% EQU 2 (
	bcdedit /set {default} safeboot network 1>nul
) else (
	bcdedit /set {default} safeboot minimal 1>nul
)
if %tmpERRORLEVEL% EQU 3 bcdedit /set {default} safebootalternateshell 1>nul
echo Safe mode variables set^^! To exit, re-launch this script and choose "(4) Exit safe mode"
echo Reboot now?
choice
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:exitSafeMode
bcdedit /deletevalue safeboot 1>nul
bcdedit /deletevalue safebootalternateshell 1>nul
echo Safe mode variables deleted^^! Rebooting will now boot normally
echo Reboot now?
choice
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:cleanBoot
exit /b 0


:sysinfo
echo Exporting system info to file...
start /wait msinfo32 /report %USERPROFILE%\Desktop\DanielIsCool.txt
REM Download a program to put the file into your clipboard
REM  --location = follow redirects
if not exist %TEMP%\file2clip.exe curl %file2clipURL% --silent --location --output %TEMP%\file2clip.exe
REM Put the report file into the clipboard for convenience
%TEMP%\file2clip.exe %USERPROFILE%\Desktop\DanielIsCool.txt
echo A report file has been generated and put on your desktop ^& into your clipboard
pause
exit /b 0


:enterBIOS
bcdedit | find "winload.efi"
if %ERRORLEVEL% EQU 0 (
	echo Press any key to reboot to BIOS...
	>nul pause
	shutdown /r /soft /t 0 /fw
) else (
	echo Your device does not support booting into BIOS automatically.
	echo Opening up Wiki article on manually entering BIOS...
	start %legacyBIOSURL%
	echo Press any key to return to the main menu...
	>nul pause
	exit /b 0
)


REM Internal stuff

:checkPermissions
net session 1>nul 2>nul
if %ERRORLEVEL% NEQ 0 (
	echo The script was not started using administrative permissions
	powershell -Command "Start-Process -FilePath 'cmd' -ArgumentList '/K %~dpnx0' -Verb RunAs"
	exit
)
exit /b 0

:checkSafeMode
for /f "skip=1 delims=" %%a in ('wmic computersystem get BootupState') do for /f "delims=" %%b in ("%%a") do set state=%%b
call :trimString state %state%
set inSafeMode=1
if "%state%" EQU "Normal boot" set inSafeMode=0

:trimString
set Params=%*
setlocal
for /f "tokens=1*" %%a in ("!Params!") do EndLocal & set %1=%%b
exit /b
