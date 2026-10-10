@echo off
chcp 65001 >nul
title SiliconFlow API Key Test
echo.
echo   SiliconFlow API key self-test
echo   Please DISCONNECT your VPN before testing.
echo.
python "%~dp0test_siliconflow.py"
