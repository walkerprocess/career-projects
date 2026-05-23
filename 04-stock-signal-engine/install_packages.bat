@echo off
chcp 65001 >nul
echo ========================================
echo    패키지 설치 (로컬 환경)
echo ========================================
echo.

:: 현재 디렉토리 확인
echo 현재 디렉토리: %CD%
echo.

:: 로컬 환경 사용 안내
echo 로컬 Python 환경을 사용합니다.
echo.

:: pip 업그레이드
echo pip을 최신 버전으로 업그레이드합니다...
python -m pip install --upgrade pip
echo.

:: requirements.txt에서 패키지 설치
echo requirements.txt에서 모든 패키지를 설치합니다...
pip install -r requirements.txt
echo.

:: curl-cffi 별도 설치 (혹시 모를 경우)
echo curl-cffi 패키지를 별도로 설치합니다...
pip install curl-cffi==0.6.0
echo.

:: 설치 확인
echo 설치된 패키지를 확인합니다...
python -c "import streamlit, yfinance, openai, pandas, requests, bs4, plotly, dotenv, curl_cffi, openpyxl; print('모든 패키지가 성공적으로 설치되었습니다!')"
if errorlevel 1 (
    echo 일부 패키지 설치에 문제가 있습니다.
    echo 수동으로 설치해주세요.
) else (
    echo.
    echo ✅ 모든 패키지 설치가 완료되었습니다!
)

echo.
echo 패키지 설치가 완료되었습니다.
pause 