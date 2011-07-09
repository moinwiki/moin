echo off
echo.
echo This is the windows version of the "quickinstall" file.
echo It requires the stand-alone wget.exe from http://users.ugent.be/~bpuype/wget/#download
echo and 7za.exe from http://sourceforge.net/projects/sevenzip/files/7-Zip/9.20/7za920.zip/download
echo.
echo wget.exe and 7za.exe must be installed in the system path or this directory.
echo.

echo Creating a virtual environment in directory env/ ...
virtualenv --no-site-packages env

echo Activating virtual environment ...
call env\Scripts\activate.bat

echo Getting some 3rd party stuff and unpack them into env/, where the default
echo wikiconfig.py expects them (should be replaced by packaging) ...

del /q env\*.tar

echo Installing babel first ...
pip install babel

echo Installing XStatic first ...
pip install XStatic==0.0.1

echo Installing all required python packages from pypi ...
pip install -e .

echo Compiling translations (not required if wiki is English only) ...
python setup.py compile_catalog --statistics



