@echo off
title 24HS Automator
set version=1.0.0
REM Needed to fill in variables inside if statements
setlocal EnableDelayedExpansion

REM Setup a place to store all data
set dataStorage=%TEMP%\24HS-Automator
REM Make sure that folder exists
if not exist %dataStorage%\nul mkdir %dataStorage%

REM Some stuff here might need changing every once in a while
REM OS Info
set win10versionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/win10.txt
set nvidiaVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/nvidiaGPU.txt
set amdVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/amdGPU.txt
set file2clipURL=https://github.com/CommandMC/24HS-Automator/raw/main/tools/file2clip.exe
set manjaroURL=https://osdn.net/dl/manjaro/manjaro-kde-20.2.1-minimal-210103-linux59.iso
set legacyBIOSURL=https://www.reddit.com/r/24hoursupport/wiki/enteringbios#wiki_cannot_boot_into_system_or_legacy_.28non_uefi.29_board
set hirensURL=https://www.hirensbootcd.org/files/HBCD_PE_x64.iso
set memtestURL=https://www.memtest86.com/downloads/memtest86-usb.zip

REM Go into the script's location (change drive letter, cd into directory)
REM This is only necessary because we're (usually) running the script as administrator (and those start out inside Sys32)
%~d0
cd %~dp0

REM Check if the script was ran with administrative permissions. If not, run it with them
call :checkPermissions

REM Check if we're currently running in safe mode (to either display "Enter"- or "Exit safe mode")
call :checkSafeMode

REM Check the scripts requirements
call :checkRequirements

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


:systemUpToDate winVersion
curl %win10versionInfo% --silent --location --output %dataStorage%\win10.txt
call :readLineFromFile "%dataStorage%\win10.txt" 1 latestWindowsVersion
REM If a Windows version wasn't supplied, try to get the current one out of the registry
if "%1" EQU "" (
	REM Tries to get the display name out of the registry
	for /f "tokens=3 skip=2" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "DisplayVersion" 2^>nul') do set currentVersion=%%a 1>nul 2>nul
	REM This reg key does not exist in Win versions older than 20H2.
	REM Since running a command inside a for loop does not set the errorlevel, we have to run it again to actually know if it exists
	reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "DisplayVersion" 1>nul 2>nul
	REM As mentioned, if this key does not exist we know we're out of date
	if !ERRORLEVEL! NEQ 0 set currentVersion=2004
) else (
	set currentVersion=%1
)
REM Compare that to the set value
if %currentVersion% EQU %latestWindowsVersion% (
	echo Major Windows version is up to date^^!
	echo Opening Settings and searching for minor updates there...
	REM Open up the Settings' Update tab
	control update
	REM Kick off the Update Session Orchestrator to start searching for updates
	REM All switches for that tool are listed at https://www.urtech.ca/2018/11/usoclient-documentation-switches/
	usoclient StartInteractiveScan
	echo.
	echo Also checking for GPU driver updates...
	call :getWMICvalue GPUManufacturer 1 path win32_VideoController get AdapterCompatibility
	call :trimString GPUManufacturer !GPUManufacturer!
	if "!GPUManufacturer!" EQU "NVIDIA" (
		REM Download version info
        curl %nvidiaVersionInfo% --silent --location --output %dataStorage%\nvidiaVersionInfo.txt
		REM Read the actual version out of the file
        call :readLineFromFile "%dataStorage%\nvidiaVersionInfo.txt" 1 latestNVIDIAVersion
		REM Get the current driver version using WMIC
        call :getWMICvalue currentDriverVersion 1 path win32_VideoController get DriverVersion
		REM Do some string manipulation to format the current version nicely
        set currentDriverVersion=!currentDriverVersion:~-6,1!!currentDriverVersion:~-4,4!
        set currentDriverVersion=!currentDriverVersion:~0,3!.!currentDriverVersion:~3!
		REM Actually compare the two versions
        if !currentDriverVersion! EQU !latestNVIDIAVersion! (
            echo Your NVIDIA GPU drivers are up to date!
        ) else (
			echo Your NVIDIA GPU drivers are not up to date. Press any key to download the latest installer...
			pause >nul
			call :readLineFromFile "%dataStorage%\nvidiaVersionInfo.txt" 2 latestNVIDIADriver
			curl !latestNVIDIADriver! --location --output %dataStorage%\latestNVIDIADriver.exe
			%dataStorage%\latestNVIDIADriver.exe
		)
	) else if "!GPUManufacturer!" EQU "Advanced Micro Devices, Inc." (
		REM Download version info
		curl %amdVersionInfo% --silent --location --output %dataStorage%\amdVersionInfo.txt
		REM Read the actual version out of the file
		call :readLineFromFile "%dataStorage%\amdVersionInfo.txt" 1 latestAMDVersion
		REM As far as I know it isn't possible to read out the current AMD driver version using CMD
		REM This is ugly, but at least it works
        echo You're using an AMD GPU. Automatically checking for updates is currently not supported.
		echo Please check your driver version manually. The latest version is !latestAMDVersion!
		echo If your driver version is NOT the same as above, press N
		echo If they are the same, press Y
		choice /c YN
		if !ERRORLEVEL! EQU 1 (
			echo Your AMD GPU drivers are up to date!
		) else (
			echo Your AMD GPU drivers are not up to date. Press any key to download the latest installer...
			pause >nul
			REM Read out the latest driver download link
			call :readLineFromFile "%dataStorage%\amdVersionInfo.txt" 2 latestAMDDriver
			REM AMD downloads require a HTTP referer set to their own site, otherwise they will error out
			call :readLineFromFile "%dataStorage%\amdVersionInfo.txt" 3 AMDreferer
			REM Download the latest driver with the referer set correctly
			curl !latestAMDDriver! --referer !AMDreferer! --location --output %dataStorage%\latestAMDDriver.exe
			%dataStorage%\latestAMDDriver.exe
		)
	) else (
        echo We do not support checking for GPU driver updates on your model yet.
        echo Please search for them manually. Your GPU manufacturer is !GPUManufacturer!
	)
) else (
	echo You're not on the latest Windows version^^! Downloading and launching update assistant...
	REM --location = follow redirects
	call :readLineFromFile "%dataStorage%\win10.txt" 3 updateAssistantURL
	if not exist %dataStorage%\updateAssistant.exe curl !updateAssistantURL! --silent --location --output %dataStorage%\updateAssistant.exe
	%dataStorage%\updateAssistant.exe
)
echo.
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
if not exist %dataStorage%\file2clip.exe curl %file2clipURL% --silent --location --output %dataStorage%\file2clip.exe
REM Put the report file into the clipboard for convenience
%dataStorage%\file2clip.exe %USERPROFILE%\Desktop\DanielIsCool.txt
echo A report file has been generated and put on your desktop ^& into your clipboard
pause
exit /b 0


:enterBIOS
bcdedit | find "winload.efi" 1>nul 2>nul 
if %ERRORLEVEL% EQU 0 (
	echo Press any key to reboot to BIOS...
	>nul pause
	REM /soft and /fw are exclusive
	shutdown /r /t 0 /fw
) else (
	echo Your device does not support booting into BIOS automatically.
	echo Opening up Wiki article on manually entering BIOS...
	start %legacyBIOSURL%
	echo Press any key to return to the main menu...
	>nul pause
)
exit /b 0


REM
REM
REM Internal stuff
REM
REM


:checkPermissions
net session 1>nul 2>nul
if %ERRORLEVEL% NEQ 0 (
	echo The script was not started using administrative permissions
	powershell -Command "Start-Process -FilePath 'cmd' -ArgumentList '/K %~dpnx0' -Verb RunAs"
	exit
)
exit /b 0

:checkSafeMode
call :getWMICvalue state 1 computersystem get BootupState
set inSafeMode=1
if "%state%" EQU "Normal boot" set inSafeMode=0
exit /b 0

:checkRequirements
1>nul 2>nul where tar
if %ERRORLEVEL% EQU 1 (
	echo ERROR: This script requires the CURL and TAR commands, which are included with W10 1803.
	echo Please update to at least 1803 manually.
	exit
)
exit /b 0

:trimString storageVar string
REM Removes leading and trailing whitespaces from a string and stores it inside storageVar
set Params=%*
setlocal
for /f "tokens=1*" %%a in ("%Params%") do EndLocal & set %1=%%b
exit /b

:readLineFromFile file lineNum storageVar
REM Reads one line out of a file and sets the specified variable to its contents
set /a skip=%2-1
REM This is a bit ugly since we have to check for skip=0 (otherwise for will always fail)
if %skip% EQU 0 (
    set skip=
) else (
    set skip=skip=%skip% 
)
for /f "%skip%delims=" %%a in (%~1) do if not defined done (
    set done=1
    set %3=%%a
)
set skip=
set done=
exit /b 0

:getWMICvalue storageVar valueIndex args[]
REM Runs a WMIC call and stores the resulting value inside storageVar
REM ValueIndex decides which result to return (used for example for multiple drives inside :isoFlash)
REM Capture all parameters except the first and second inside a variable
for /f "tokens=1,2*" %%a in ("%*") do set allParams=%%c
REM Launch wmic with those params and store the result inside param 1
for /f "skip=%2 delims=" %%a in ('wmic %allParams%') do for /f "delims=" %%b in ("%%a") do set %1=%%b
REM Remove leading & trailing whitespaces from the output
call :trimString %1 !%1!
REM Free up allParams since we don't need it anymore
set allParams=
exit /b 0
