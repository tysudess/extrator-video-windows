@echo off
setlocal
cd /d "%~dp0"

py -3.12 -m pip install -r requirements.txt
if errorlevel 1 goto :erro

if not exist bin mkdir bin

echo.
echo O build local exige que os arquivos abaixo estejam em bin:
echo   bin\yt-dlp.exe
echo   bin\ffmpeg.exe
echo   bin\ffprobe.exe
echo   bin\deno.exe
echo.
if not exist bin\yt-dlp.exe goto :faltou
if not exist bin\ffmpeg.exe goto :faltou
if not exist bin\ffprobe.exe goto :faltou
if not exist bin\deno.exe goto :faltou
if not exist ExtratorVideos-Icone.ico goto :icone

py -3.12 -m py_compile main.py novo_layout.py modern_layout.py refined_layout.py refined_layout_v2.py range_slider.py advanced_editor.py
if errorlevel 1 goto :erro

py -3.12 -m PyInstaller --noconfirm --clean --windowed --onedir --name ExtratorVideos --contents-directory _internal --icon ExtratorVideos-Icone.ico refined_layout_v2.py
if errorlevel 1 goto :erro

xcopy /E /I /Y bin dist\ExtratorVideos\bin >nul
copy /Y LEIA-ME.txt dist\ExtratorVideos\LEIA-ME.txt >nul
copy /Y ExtratorVideos-Icone.ico dist\ExtratorVideos\ExtratorVideos-Icone.ico >nul

echo.
echo Build v2.0 concluido em dist\ExtratorVideos
pause
exit /b 0

:faltou
echo ERRO: faltam executaveis na pasta bin.
pause
exit /b 1

:icone
echo ERRO: ExtratorVideos-Icone.ico nao foi encontrado.
pause
exit /b 1

:erro
echo ERRO durante o build.
pause
exit /b 1
