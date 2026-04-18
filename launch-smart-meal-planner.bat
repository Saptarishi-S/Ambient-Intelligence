@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0launch-smart-meal-planner.ps1"
if errorlevel 1 (
  echo.
  echo Launcher failed. Read the message above.
  pause
)
