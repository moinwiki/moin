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

wget -nc "http://download.cksource.com/CKEditor/CKEditor/CKEditor 3.5/ckeditor_3.5.tar.gz" -Penv/
7za x env/ckeditor_3.5.tar.gz -y -oenv\
7za x env/ckeditor_3.5.tar -y -oenv\

wget -nc http://static.moinmo.in/files/packages/TWikiDrawPlugin-moin.tar.gz -Penv/
7za x env/TWikiDrawPlugin-moin.tar.gz -y -oenv\
7za x env/TWikiDrawPlugin-moin.tar -y -oenv\

wget -nc http://static.moinmo.in/files/packages/svg-edit.tar.gz -Penv/
7za x env/svg-edit.tar.gz -y -oenv\
7za x env/svg-edit.tar -y -oenv\

mkdir env\jquery
wget -nc http://code.jquery.com/jquery-1.4.4.min.js -Oenv/jquery/jquery.min.js

wget -nc http://svgweb.googlecode.com/files/svgweb-2010-08-10-Owlephant-1.zip -Penv/
7za x env/svgweb-2010-08-10-Owlephant-1.zip -y -oenv\

wget -nc http://downloads.sourceforge.net/project/anywikidraw/anywikidraw/anywikidraw-0.14/anywikidraw-0.14.zip?use_mirror=ignum -Penv/
7za x env/anywikidraw-0.14.zip -y -oenv\
xcopy "env\AnyWikiDraw 0.14" env\AnyWikiDraw\ /Y /E /H

del /q env\*.tar

echo Installing babel first ...
pip install babel

echo Installing all required python packages from pypi ...
pip install -e .

echo Compiling translations (not required if wiki is English only) ...
python setup.py compile_catalog --statistics



