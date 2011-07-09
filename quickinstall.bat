echo off
echo.
echo This is the windows version of the "quickinstall" file.
echo.

echo Creating a virtual environment in directory env/ ...
virtualenv --no-site-packages env

echo Activating virtual environment ...
call env\Scripts\activate.bat

echo Installing babel first ...
pip install babel

echo Installing XStatic first ...
pip install XStatic==0.0.1

echo Installing all required python packages from pypi ...
pip install -e .

echo Compiling translations (not required if wiki is English only) ...
python setup.py compile_catalog --statistics

