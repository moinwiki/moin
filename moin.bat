echo off
echo.
echo This executes the "moin" file under Windows.  Read the "moin" file for options.
echo.
echo Activating Python environment...
call env\Scripts\activate.bat
echo.
echo Starting server... Press Ctrl-c keys to stop server, 
echo then reply N to deactivate environment.

if "%1"=="moin" goto Onemoin

echo on
python moin moin %*
goto Deactivate

:Onemoin
echo on
python moin %*

:Deactivate
echo off
echo.
echo Deactivating Python environment...
call env\Scripts\deactivate.bat
