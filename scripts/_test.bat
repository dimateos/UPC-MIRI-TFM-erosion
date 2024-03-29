@echo off
echo Just exit from test .bat
EXIT /b

REM using ./env works for multiple commands otherwise exits at the first
::CALL ./env
::%bpy% --version
::%bpy% --version

REM check packages to it
bpy --version
bpy -c "help(\"modules\")"
bpip freeze
bpip list -v

REM NOTE: local pip will still try to access Python roaming packages, whereas blender python wont
REM         so it wont install requirements already satisfied there, maybe with --force-reinstall?
REM %bpackages% forces to be installed in the local folder, otehrwise pip could skip it

REM backup env (using some common external .bat)
bpip_backup code

REM voro++ interface for this python version...
bpip install wheel
bpip install setuptools-scm
bpip install setuptools
REM used for tests in the other repo
%bpip% install pytest -t %bpackages%
REM autocomplete for bpy and bmesh etc
bpip install fake-bpy-module-3.4

::... done with install deps (note that the shared blender installation has all modules already)

REM all fail when compiling c++ interface... 'Python.h': No such file or directory
REM had to install a full python dev env on top of Blenders
bpip install tess
bpip install git+https://github.com/eleftherioszisis/tess
bpip install git+https://github.com/joe-jordan/pyvoro@feature/python3

REM own updated fork or local version
bpip install --force-reinstall git+https://github.com/dimateos/UPC-MIRI-TFM-tess
bpip install --upgrade git+https://github.com/dimateos/UPC-MIRI-TFM-tess
bpip install ../DATA/UPC-MIRI-TFM-tess
bpip uninstall tess

REM editable flag for lacally developed packages (no reinstalling), same as setup.py develop
REM NOTE: pip recognizes the remote git and adds that URL instead of path, not documented tho
REM BUT: it seems that I still need to recompile cython manually tho... I leverage this to the testing setup
bpip install --editable ../DATA/UPC-MIRI-TFM-tess
REM NOTE: it seems I can have both installs, local and editable at the sametime?
REM maybe because the setup actually uses setup.py direclty not pip
bpy setup.py develop &REM needs to be executed at the root of the library repository

::... done with update.bat
