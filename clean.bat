@echo off
echo Cleaning Python cache and junk...

:: Delete __pycache__ folders
for /d /r %%d in (__pycache__) do (
    echo Deleting %%d
    rmdir /s /q "%%d"
)

:: Delete .pyc and .pyo files
for /r %%f in (*.pyc *.pyo) do (
    del /q "%%f"
)

:: Delete junk files
for /r %%f in (.DS_Store *~ *.tmp) do (
    del /q "%%f"
)

:: Delete __pypackages__ folders
for /d /r %%d in (__pypackages__) do (
    echo Deleting %%d
    rmdir /s /q "%%d"
)

:: Delete logs folders
for /d /r %%d in (logs) do (
    echo Deleting %%d
    rmdir /s /q "%%d"
)

:: Delete downloads folders
for /d /r %%d in (downloads) do (
    echo Deleting %%d
    rmdir /s /q "%%d"
)

:: Delete images folders
for /d /r %%d in (images) do (
    echo Deleting %%d
    rmdir /s /q "%%d"
)

echo Cleanup complete!
pause