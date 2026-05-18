# Vision / YOLO PC 설치 가이드

이 문서는 Vision PC 담당자만 보면 됩니다.

Robot Controller, HMI, Docker, Robot 직접 제어는 설치하지 않습니다.  
Vision PC는 카메라를 보고 PLC에 결과만 전달합니다.

## 1. 위치별 역할

| PC | 실행 파일 | 역할 | 연결 PLC |
|---|---|---|---|
| Vision A | `A_Process_pendant.py` | QR 스캔, 차종 트리거 | PLC150, PLC160 |
| Vision B | `B_Process_pendant.py` | YOLO 검사, OK/NG 통보 | PLC140, PLC160 |
| Vision C | `C_Process_pendant.py` | YOLO 검사, 종합 처리 | PLC120, PLC160 |

DB는 Robot Controller PC의 MySQL을 사용합니다.

```text
MySQL IP: 192.168.3.141
DB: faictory_mes
User: guest
Password: guest1234
```

Vision 스크립트 안의 표준 DB 설정은 아래와 같습니다.

```python
DB_CONFIG = {
    'host': '192.168.3.141',
    'port': 3306,
    'user': 'guest',
    'password': 'guest1234',
    'db': 'faictory_mes',
    'charset': 'utf8mb4',
    'autocommit': True,
    'use_unicode': True,
    'init_command': "SET NAMES utf8mb4"
}
```

설치 스크립트는 `factory_mes` 원본 코드의 `localhost/root/1234` 값을 위 값으로 자동 변경합니다.

## 2. Windows 기본 설치

관리자 PowerShell을 열고 실행합니다.

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.11 -e
```

설치 후 PowerShell을 다시 열고 확인합니다.

```powershell
git --version
py --version
```

## 3. Vision A PC 설치

Vision A는 QR 스캐너/카메라 담당입니다.

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role A
```

더 쉬운 방법:

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\setup_vision_A.bat
```

실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-start.ps1 -Role A
```

또는 아래 파일을 더블클릭합니다.

```text
C:\Busan_Project\factory_mes\run_vision_A.bat
```

또는 이 파일을 더블클릭합니다.

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\start_vision_A.bat
```

## 4. Vision B PC 설치

Vision B는 YOLO 검사 담당입니다.

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role B
```

더 쉬운 방법:

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\setup_vision_B.bat
```

YOLO 모델 파일을 아래 위치에 둡니다.

```text
C:\Busan_Project\factory_mes\C_VISION.pt
```

실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-start.ps1 -Role B
```

또는 아래 파일을 더블클릭합니다.

```text
C:\Busan_Project\factory_mes\run_vision_B.bat
```

또는 이 파일을 더블클릭합니다.

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\start_vision_B.bat
```

## 5. Vision C PC 설치

Vision C는 YOLO 검사와 최종 종합 처리 담당입니다.

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role C
```

더 쉬운 방법:

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\setup_vision_C.bat
```

YOLO 모델 파일을 아래 위치에 둡니다.

```text
C:\Busan_Project\factory_mes\C_VISION.pt
```

실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-start.ps1 -Role C
```

또는 아래 파일을 더블클릭합니다.

```text
C:\Busan_Project\factory_mes\run_vision_C.bat
```

또는 이 파일을 더블클릭합니다.

```text
C:\Busan_Project\Indy7_HMI_Clean\deployment\windows\start_vision_C.bat
```

## 6. 카메라 번호가 다를 때

카메라가 안 열리면 카메라 번호를 바꿔 설치 스크립트를 다시 실행합니다.

예: Vision B 카메라가 0번일 때

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role B -CameraIndex 0
```

예: Vision C 카메라가 1번일 때

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role C -CameraIndex 1
```

## 7. 통신 확인

Vision A:

```powershell
Test-NetConnection 192.168.3.150 -Port 2000
Test-NetConnection 192.168.3.160 -Port 2000
Test-NetConnection 192.168.3.141 -Port 3306
```

Vision B:

```powershell
Test-NetConnection 192.168.3.140 -Port 2000
Test-NetConnection 192.168.3.160 -Port 2000
Test-NetConnection 192.168.3.141 -Port 3306
```

Vision C:

```powershell
Test-NetConnection 192.168.3.120 -Port 2000
Test-NetConnection 192.168.3.160 -Port 2000
Test-NetConnection 192.168.3.141 -Port 3306
```

`TcpTestSucceeded : True`이면 해당 장비까지 포트가 열려 있는 상태입니다.

## 8. YOLO만 쓰는 사람용 요약

Vision B:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role B
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-start.ps1 -Role B
```

Vision C:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role C
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-start.ps1 -Role C
```

YOLO PC 담당자는 Docker Desktop을 설치하지 않아도 됩니다.
