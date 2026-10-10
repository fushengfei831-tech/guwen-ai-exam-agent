@echo off
chcp 65001 >nul
title Ancient Chinese Corpus Converter
echo.
echo   Converting chinese-poetry JSON  ==^>  Dify-ready txt
echo   Please wait, this may take a few minutes.
echo.
python "%~dp0convert_poetry.py"
