::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFB5YSRKDAE+1EbsQ5+n//Naq7EQeW4I=
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCyDJGqR9lUxMTpGXg2UPWeFIZwowN3Z0+aGt0MeXKw6YIq7
::YB416Ek+ZG8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off

:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo 관리자 권한으로 프로그램을 다시 시작하는 중입니다.
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params = %*:"=""
    echo UAC.ShellExecute "cmd.exe", "/c %~s0 %params%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"

:start
cls
echo 1. 프로그램 시작(Launch Program)
echo 2. API 키 설정(Set API Key)
echo 3. 대상 역 설정(Set Target Station)
echo 4. 종료(Exit)
set /p a=선택(Select): 
if %a%==1 goto run
if %a%==2 goto api
if %a%==3 goto stn
if %a%==4 goto exit
set a=
goto start
:run
cls
start ./main.exe
:api
cls
echo 서울열린데이터광장에서 발급받은 API키를 입력해주세요.
echo Please enter the API key.
set /p b=입력(Enter):
echo %b%>>"./api_key.txt"
set b=
goto start
:stn
cls
echo 전광판에 표시할 역 이름을 입력해주세요.
echo Please enter the station name.
set /p c=입력(Enter):
echo %c%>>"./stn_to_show.txt"
set c=
goto start
:exit
exit