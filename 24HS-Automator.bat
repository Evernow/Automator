@echo off
title 24HS Automator
set version=1.0.0
REM Needed to fill in variables inside if statements
setlocal EnableDelayedExpansion

REM Setup a place to store all data
set dataStorage=%TEMP%\24HS-Automator
REM Make sure that folder exists
if not exist "%dataStorage%\" mkdir "%dataStorage%"

REM Some stuff here might need changing every once in a while
REM Version Info/Download links
set win10versionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/win10.txt
set nvidiaVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/nvidiaGPU.txt
set amdVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/amdGPU.txt
set rufusVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/rufus.txt
set balenaCliVersionInfo=https://raw.githubusercontent.com/CommandMC/24HS-Automator/main/versions/balena_cli.txt
set manjaroDownloadLink=https://raw.githubusercontent.com/Evernow/evernowmanjaro/main/LatestISO.txt
set manjaroChecksumURL=https://raw.githubusercontent.com/Evernow/evernowmanjaro/main/LatestISOChecksumMD5.txt

REM Tools
set file2clipURL=https://github.com/CommandMC/24HS-Automator/raw/main/tools/file2clip.exe
set gdownURL=https://github.com/CommandMC/24HS-Automator/raw/main/tools/gdown.exe
set openFileBoxURL=https://github.com/CommandMC/24HS-Automator/raw/main/tools/OpenFileBox.exe

REM External links
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
echo (5) (TODO) Perform clean boot
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
choice /c YN
REM /soft = Wait for programs to quit
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:systemUpToDate winVersion
curl %win10versionInfo% --silent --location --output "%dataStorage%\win10.txt"
call :readLineFromFile "%dataStorage%\win10.txt" 1 latestWindowsVersion
REM If a Windows version wasn't supplied, try to get the current one out of the registry
if "%1" EQU "" (
	call :getWinVersion currentVersion
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
	call :checkGPUUpdates !GPUManufacturer!
) else (
	echo You're not on the latest Windows version^^! Downloading and launching update assistant...
	call :readLineFromFile "%dataStorage%\win10.txt" 3 updateAssistantURL
	REM --location = follow redirects
	if not exist "%dataStorage%\updateAssistant.exe" curl !updateAssistantURL! --silent --location --output "%dataStorage%\updateAssistant.exe"
	"%dataStorage%\updateAssistant.exe"
)
echo.
echo Press any key to return to the main menu...
>nul pause
exit /b 0


:checkGPUUpdates manufacturer
REM Tries to check for GPU driver updates. Currently only supports NVIDIA GPUs
if "%1" EQU "NVIDIA" (
	REM Download version info
	curl %nvidiaVersionInfo% --silent --location --output "%dataStorage%\nvidiaVersionInfo.txt"
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
		curl !latestNVIDIADriver! --location --output "%dataStorage%\latestNVIDIADriver.exe"
		"%dataStorage%\latestNVIDIADriver.exe"
	)
) else if "%1" EQU "Advanced Micro Devices, Inc." (
	REM Download version info
	curl %amdVersionInfo% --silent --location --output "%dataStorage%\amdVersionInfo.txt"
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
		curl !latestAMDDriver! --referer !AMDreferer! --location --output "%dataStorage%\latestAMDDriver.exe"
		"%dataStorage%\latestAMDDriver.exe"
	)
) else (
	echo We do not support checking for GPU driver updates on your model yet.
	echo Please search for them manually. Your GPU manufacturer is !GPUManufacturer!
)
exit /b 0


:isoFlash
call :selectISO selectedISO noFlash osType
if %ERRORLEVEL% NEQ 0 (
	echo There was an error when selecting an ISO file. Errorlevel is %ERRORLEVEL%.
	echo Press any key to return to the main menu...
	pause >nul
	exit /b %ERRORLEVEL%
)
REM If we don't have to use the flashing tool, we're done now
if "%noFlash%" EQU "1" (
	exit /b 0
)
REM Launch up the USB drive selector
call :selectUSBDrive USBdriveIndex USBdriveName
if %ERRORLEVEL% NEQ 0 (
	echo There was an error when selecting a USB drive. Errorlevel is %ERRORLEVEL%.
	echo Press any key to return to the main menu...
	pause >nul
	exit /b %ERRORLEVEL%
)
echo.
echo Selected ISO:             %selectedISO%
echo Selected USB drive name:  %USBdriveName%
echo Are you absolutely sure these settings are correct? Choosing the wrong device here will lead to data loss!
choice /c YN
if %ERRORLEVEL% EQU 2 (
	echo Returning to main menu...
	exit /b 0
)
echo Cleaning USB drive NOW. Do not unplug the drive!
call :cleanUSB %USBdriveIndex% "%USBdriveName%" cleanedDriveLetter

echo Downloading flashing program, please wait...
if "%osType%" EQU "windows" (
	curl %rufusVersionInfo% --silent --location --output "%dataStorage%\rufus.txt"
	call :readLineFromFile "%dataStorage%\unetbootin.txt" 2 rufusDownloadLink
	curl !rufusDownloadLink! --silent --location --output "%dataStorage%\rufus.exe"
	set command="%dataStorage%\rufus.exe" -i %selectedISO%
	echo.
	echo Important: In the Rufus window that'll pop up, select the
	echo "Select Me" device at the top and press "Start". Do not change
	echo any other setting!
	echo.
	pause
) else (
	curl %balenaCliVersionInfo% --silent --location --output "%dataStorage%\balena_cli.txt"
	call :readLineFromFile "%dataStorage%\balena_cli.txt" 2 balenaCliDownloadLink
	curl !balenaCliDownloadLink! --silent --location --output "%dataStorage%\balena-cli.zip"
	if not exist "%dataStorage%\balena-cli\" mkdir "%dataStorage%\balena-cli"
	tar -xf "%dataStorage%\balena-cli.zip" -C "%dataStorage%"
	set command="%dataStorage%\balena-cli\balena.exe" local flash "%selectedISO%" -d \\.\PhysicalDrive%USBdriveIndex% -y
)
echo Running %command%
%command%
echo Flash complete^^! Press any key to return to the main menu...
pause >nul
exit /b 0


:selectISO selectedISOvar noFlashVar osTypeVar
curl %win10versionInfo% --silent --location --output "%dataStorage%\win10.txt"
call :readLineFromFile "%dataStorage%\win10.txt" 1 latestWindowsVersion
call :readLineFromFile "%dataStorage%\win10.txt" 2 winISO
call :readLineFromFile "%dataStorage%\win10.txt" 4 winMediaCreationTool
curl %manjaroDownloadLink% --silent --location --output "%dataStorage%\manjaro.txt"
call :readLineFromFile "%dataStorage%\manjaro.txt" 1 manjaroISO
echo Which ISO do you want to flash?
echo Auto-Download:
echo (1) Windows 10 (%latestWindowsVersion%, using ISO)
echo (2) Hiren's BootCD
echo (3) Memtest86
echo (4) Manjaro Linux
echo (5) Windows 10 (%latestWindowsVersion%, using Media Creation Tool)
echo Custom:
echo (6) Select ISO file
choice /c 123456 /N
echo.
if %ERRORLEVEL% EQU 1 (
	echo Downloading Windows 10 %latestWindowsVersion%. Please wait...
	REM Check if the ISO already exists. We wouldn't want to download a 6GB file twice
	if exist "%dataStorage%\win10ISO.iso" (
		REM Ask the user if they want to use the existing file or download the new one
		echo The ISO file already exists in temp storage. Do you want to use the existing one?
		choice /c YN
		REM If they want to download it again, start the download
		if !ERRORLEVEL! EQU 2 curl %winISO% --location --output "%dataStorage%\win10ISO.iso"
	) else (
		REM If the ISO doesn't exist already, just download it
		curl %winISO% --location --output "%dataStorage%\win10ISO.iso"
	)
	REM Whatever happened up there, the ISO should now be here
	REM (provided the user didn't cancel the download, but then they're on their own anyways)
	set %1=%dataStorage%\win10ISO.iso
	set %3=windows
) else if %ERRORLEVEL% EQU 2 (
	REM Do the same thing as above, just for the Hirens ISO
	REM See above for detailed comments
	echo Downloading Hiren's BootCD. Please wait...
	if exist "%dataStorage%\hirensISO.iso" (
		echo The ISO file already exists in temp storage. Do you want to use the existing one?
		choice /c YN
		if !ERRORLEVEL! EQU 2 curl %hirensURL% --location --output "%dataStorage%\hirensISO.iso"
	) else (
		curl %hirensURL% --location --output "%dataStorage%\hirensISO.iso"
	)
	set %1=%dataStorage%\hirensISO.iso
	set %3=windows
) else if %ERRORLEVEL% EQU 3 (
	if not exist "%dataStorage%\memtest\memtest86-usb.img" (
		REM Memtest comes in a ZIP file with a tool to flash it onto a drive.
		REM We'll not use that tool and instead just unzip it and use the IMG file
		echo Downloading and unzipping Memtest86. Please wait...
		curl %memtestURL% --location --output "%dataStorage%\memtest.zip"
		if not exist "%dataStorage%\memtest\" mkdir "%dataStorage%\memtest"
		tar -xf "%dataStorage%\memtest.zip" -C "%dataStorage%\memtest"
	)
	set %1=%dataStorage%\memtest\memtest86-usb.img
	set %3=linux
) else if %ERRORLEVEL% EQU 4 (
	echo Downloading Manjaro ISO. Please wait...
	REM Since Dan's ISO downloads are on Google Drive,
	REM we have to use a separate download tool (gdown). This is downloaded here.
	REM Edit: No longer downloaded just here, a little further below
	if exist "%dataStorage%\manjaroISO.iso" (
		echo The ISO file already exists in temp storage. Do you want to use the existing one?
		choice /c YN
		if !ERRORLEVEL! EQU 2 (
			curl %gdownURL% --silent --location --output "%dataStorage%\gdown.exe"
			"%dataStorage%\gdown.exe" --output "%dataStorage%\manjaroISO.iso" %manjaroISO%
		)
	) else (
		curl %gdownURL% --silent --location --output "%dataStorage%\gdown.exe"
		"%dataStorage%\gdown.exe" --output "%dataStorage%\manjaroISO.iso" %manjaroISO%
	)
	REM TODO: Verify the ISO file using %manjaroChecksumURL% (MD5)
	set %1=%dataStorage%\manjaroISO.iso
	set %3=linux
) else if %ERRORLEVEL% EQU 5 (
	echo Downloading Media Creation Tool. Please wait...
	curl %winMediaCreationTool% --location --output "%dataStorage%\MediaCreationTool.exe"
	"%dataStorage%\MediaCreationTool.exe"
	REM Indicate that the built-in flashing function does not need to be used here
	set %2=1
REM Screw the people that press CTRL+C on choice, you have no power here
) else (
	REM Download a program to display a file selection prompt (wouldn't want someone to type in the path manually)
	curl %openFileBoxURL% --location --silent --output "%dataStorage%\OpenFileBox.exe"
	REM OpenFileBox prints the selected file path into STDOUT, so the only ways to parse that is to either
	REM put it into a for loop or file. And since it doesn't set the ERRORLEVEL while in a for loop, we sadly
	REM have to use a temporary file
	"%dataStorage%\OpenFileBox.exe" "ISO (*.iso)|*.iso|Floppy (*.img)|*.img" "%USERPROFILE%\Downloads" "Open Disk Image File" > "%dataStorage%\selectedISO.txt"
	if !ERRORLEVEL! EQU 0 (
		call :readLineFromFile "%dataStorage%\selectedISO.txt" 1 %1
		REM Once we got that path out of the file we don't need it anymore
		del "%dataStorage%\selectedISO.txt"
	) else (
		exit /b 1
	)
	REM Set the osType based on the name: If it has "Windows" in it,
	REM it's Windows. If not, it's not
	REM TODO: Do this properly
	echo %1 | find /i "windows" > nul
	if !ERRORLEVEL! EQU 0 (
		set %3=windows
	) else (
		set %3=linux
	)
)
exit /b 0

:selectUSBDrive USBdriveIndex USBdriveName
REM Prompts the user to select a USB drive and stores the index (diskpart) and name
echo Please connect your USB drive and press any key...
pause >nul
REM Get the number of disks currently installed in the system
echo list disk > "%dataStorage%\diskpartCommand.txt"
diskpart /s "%dataStorage%\diskpartCommand.txt" > "%dataStorage%\diskpartListDisk.txt"
set numOfDisks=0
for /f "skip=8 usebackq delims=" %%a in ("%dataStorage%\diskpartListDisk.txt") do set /a numOfDisks=!numOfDisks!+1
REM Since the C drive is always connected, we have to subtract 1 here
set /a numOfDisks=%numOfDisks%-1
if %numOfDisks% EQU 0 (
	echo You only have your system disk available. Please make sure the USB drive is connected and working.
	exit /b 1
) else if %numOfDisks% EQU -1 (
	echo You have no disks connected. How did you manage that?
	exit /b 2
) else if %numOfDisks% EQU 1 (
	echo You have 1 disk connected. Do you want to flash the ISO onto it?
	echo Disk info:
	call :getDiskpartDetail 1 devName devLtrs
	echo Disk name: !devName!
	echo Disk drive letter^(s^): !devLtrs!
	choice /c YN
	if !ERRORLEVEL! EQU 2 (
		echo Returning to main menu...
		exit /b 3
	)
	set %1=1
	set %2=!devName!
	exit /b 0
) else (
	echo You have %numOfDisks% disks connected. Which one do you want to flash?
	for /l %%a in (1, 1, %numOfDisks%) do (
		call :getDiskpartDetail %%a devName devLtrs
		echo %%a. !devName!, Letters: !devLtrs!
	)
	set /p devIndex=Please enter the index of the device [1-%numOfDisks%] and press Enter: 
	REM Was the index entered greater than 0 and less than/equal to the number of disks?
	if !devIndex! GEQ 1 if !devIndex! LEQ %numOfDisks% (
		call :getDiskpartDetail !devIndex! finalDevName notNeeded
		set %1=!devIndex!
		set %2=!finalDevName!
		exit /b 0
	)
	exit /b 4
)
exit /b 0

:cleanUSB devIndex devName devLtrStorageVar
REM Runs diskparts clean command after doing some sanity checks
REM Stores the drive letter of the cleaned device into devLtrStorageVar
call :getDiskpartDetail %1 diskNameToCheck unused
REM If the supplied name and the name we got back arent the same, exit right away
REM if we wouldn't check this, it could cause data loss when the user unplugs the device
REM before this finishes (regardless of how reckless that would be)
REM %2 already contains quotes, so we don't have to add them again here
if %2 NEQ "%diskNameToCheck%" (
	echo Supplied drive name "%2" is not equal to "%diskNameToCheck%"! Aborting
	exit /b 1
)
echo sel disk %1 > "%dataStorage%\diskpartCommand.txt"
echo clean >> "%dataStorage%\diskpartCommand.txt"
echo convert mbr >> "%dataStorage%\diskpartCommand.txt"
echo create partition primary >> "%dataStorage%\diskpartCommand.txt"
REM Assign a drive letter we know (makes later operations easier)
call :getFreeDriveLetter %3
echo assign letter=!%3! >> "%dataStorage%\diskpartCommand.txt"
diskpart /s "%dataStorage%\diskpartCommand.txt" > nul
REM Turns out you can also select volumes by drive letter in diskpart
echo sel vol !%3! > "%dataStorage%\diskpartCommand.txt"
echo format fs=exFAT label="Select Me" quick >> "%dataStorage%\diskpartCommand.txt"
diskpart /s "%dataStorage%\diskpartCommand.txt" > nul
exit /b 0


:enterSafeMode
echo Which type of safe mode do you want to enter?
echo (D) Default
echo (N) With networking
echo (C) With command prompt
call :getAccountType accType
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
choice /c YN
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:exitSafeMode
bcdedit /deletevalue safeboot 1>nul
bcdedit /deletevalue safebootalternateshell 1>nul
echo Safe mode variables deleted^^! Rebooting will now boot normally
echo Reboot now?
choice /c YN
if %ERRORLEVEL% EQU 1 shutdown /r /soft /t 0
exit /b 0


:cleanBoot
exit /b 0


:sysinfo
echo Exporting system info to file...
start /wait msinfo32 /report "%USERPROFILE%\Desktop\DanielIsCool.txt"
REM Download a program to put the file into your clipboard
REM  --location = follow redirects
if not exist "%dataStorage%\file2clip.exe" curl %file2clipURL% --silent --location --output "%dataStorage%\file2clip.exe"
REM Put the report file into the clipboard for convenience
"%dataStorage%\file2clip.exe" "%USERPROFILE%\Desktop\DanielIsCool.txt"
echo A report file has been generated and put on your desktop ^& into your clipboard
pause
exit /b 0


:enterBIOS
REM Check if we're on an EFI system (only EFI systems support rebooting into "BIOS")
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
if %ERRORLEVEL% EQU 0 exit /b 0
echo The script was not started using administrative permissions
set pathToScript=%~dpnx0
powershell -Command Start-Process -FilePath 'cmd' -ArgumentList '/K \"%pathToScript%\"' -Verb RunAs
exit

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
if not exist %1 exit /b 1
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

REM This is the old "get a WMIC value" function. It behaves just like the new one, but doesn't support certain values
REM (ones with / and ? in them, probably some more) because of the :trimString function it requires
REM If issues are encountered with the new one, re-enable this one
:getWMICvalueOLD storageVar valueIndex args[]
for /f "tokens=1,2*" %%a in ("%*") do set allParams=%%c
for /f "skip=%2 delims=" %%a in ('wmic %allParams%') do for /f "delims=" %%b in ("%%a") do set %1=%%b
call :trimString %1 !%1!
set allParams=
exit /b 0

:getWMICvalue storageVar valueIndex args[]
REM Runs a WMIC call and stores the resulting value inside storageVar
REM ValueIndex decides which result to return
REM Capture all parameters except the first and second inside a variable
for /f "tokens=1,2,*" %%a in ("%*") do set allParams=%%c
set /a actualSkip=%2+1
REM Launch wmic with those params and store the result inside param 1
for /f "usebackq skip=%actualSkip% tokens=2 delims=," %%a in (`wmic %allParams% /format:csv`) do (
	if not defined done (
		set done=1
		for /f "delims=" %%b in ("%%a") do set %1=%%b
	)
)
REM Free up all temporary variables
set allParams=
set done=
set actualSkip=
exit /b 0

:getWMIClen storageVar args[]
REM Runs a WMIC call and stores the number of results inside storageVar
REM Capture all parameters except the first one inside a variable
for /f "tokens=1,*" %%a in ("%*") do set allParams=%%b
set %1=0
REM Count how many results there were, skipping the starting line (Node, ...) and the newline at the start
for /f "skip=2" %%a in ('wmic %allParams% /format:csv') do for /f %%b in ("%%a") do set /a %1=!%1!+1
set allParams=
exit /b 0


:getWinVersion storageVar
REM Tries to get the display name out of the registry
for /f "tokens=3 skip=2" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "DisplayVersion" 2^>nul') do set %1=%%a 1>nul 2>nul
REM This reg key does not exist in Win versions older than 20H2.
REM Since running a command inside a for loop does not set the errorlevel, we have to run it again to actually know if it exists
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v "DisplayVersion" 1>nul 2>nul
REM As mentioned, if this key does not exist we know we're out of date
if !ERRORLEVEL! NEQ 0 set %1=2004
exit /b 0

:getAccountType storageVar
for /f "skip=3" %%a in ('powershell -Command "Get-LocalUser | Where-Object { $_.Enabled -match \"True\"} | Select-Object PrincipalSource"') do set %1=%%a
exit /b 0

:getDiskpartDetail diskNum diskNameVar diskDrivesVar
REM Runs diskparts, selects the specified disk and runs the "detail disk" function
REM Puts the disk name into diskNameVar and the drive letters the disk is using into diskDrivesVar (formatted "D, E, F" or "None")

REM Unset specified variables
set %2=
set %3=
echo sel disk %1 > "%dataStorage%\diskpartCommand.txt"
echo detail disk >> "%dataStorage%\diskpartCommand.txt"
diskpart /s "%dataStorage%\diskpartCommand.txt" > "%dataStorage%\diskpartDetailDisk.txt"
call :readLineFromFile "%dataStorage%\diskpartDetailDisk.txt" 9 %2
REM Read out all partitions with drive letters and collect them in one variable
for /f "skip=26 usebackq tokens=3" %%a in ("%dataStorage%\diskpartDetailDisk.txt") do (
	REM Not really an easy way to make sure the thing we select is actually a drive letter
	REM For now we'll check if the thing we got is one character long
	set ltr=%%a
	if "!ltr:~1!" EQU "" set %3=!%3!, !ltr!
)

REM No drive letters
if "!%3!" EQU "" (
	set %3=None
) else (
	REM Remove the first ", " from devLtrs
	set %3=!%3:~2!
)
exit /b 0

:getFreeDriveLetter storageVar
REM Gets a free drive letter and stores it into storageVar
set allLetters=CDEFGHIJKLMNOPQRSTUVWXYZ
for /f "skip=1 delims=" %%a in ('wmic logicaldisk get caption') do for /f "delims=" %%b in ("%%a") do (
	REM Get just the drive letter out of the WMIC call
	set ltr=%%b
	set ltr=!ltr:~0,1!
	REM Remove the letter from allLetters
	for %%c in (!ltr!) do (
		set allLetters=!allLetters:%%c=!
	)
)
REM Give back the first free letter in that list
set %1=%allLetters:~0,1%
exit /b 0
