# 현장 배포 전략

가장 안전한 배포 방식은 **역할별 PC 분리 + 역할별 스크립트 배포**입니다.

## 1. 권장 배치

```text
Robot Controller PC 1대
  - HMI UI
  - Robot A/B/C controller
  - MQTT Broker
  - PLC Bridge
  - DB Worker
  - Digital Twin
  - MySQL

Vision PC A 1대
  - QR camera
  - A_Process_pendant.py
  - PLC150/PLC160 통신

Vision PC B 1대
  - YOLO camera
  - B_Process_pendant.py
  - PLC140/PLC160 통신

Vision PC C 1대
  - YOLO camera
  - C_Process_pendant.py
  - PLC120/PLC160 통신
```

## 2. 왜 이렇게 나누는가

Robot Controller PC는 로봇 3대 상태 수집과 3D 동기화, MQTT, DB 기록을 맡습니다. 이 부하는 i5-8500 / RAM 16GB급 PC로 충분합니다.

Vision YOLO는 카메라와 AI 추론 때문에 CPU/GPU 부하가 튀는 구간이 있습니다. 그래서 Robot Controller PC와 분리합니다. Vision이 멈춰도 로봇 상태 수집, PLC 감시, DB 저장은 유지됩니다.

## 3. 배포 방식

초보자 기준 최종 배포는 `.bat` 더블클릭 방식입니다.

```text
deployment/windows/setup_robot_controller.bat
deployment/windows/start_robot_controller.bat

deployment/windows/setup_vision_A.bat
deployment/windows/start_vision_A.bat

deployment/windows/setup_vision_B.bat
deployment/windows/start_vision_B.bat

deployment/windows/setup_vision_C.bat
deployment/windows/start_vision_C.bat
```

PowerShell을 직접 다룰 수 있는 사람은 아래 명령형 방식을 사용하면 됩니다.

### Robot Controller PC

배포 대상:

```text
GitHub: HeungJAELEE/Busan_Robot
Docker Compose: backend services
PowerShell script: deployment/windows/robot-controller-setup.ps1
```

처음 설치:

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\robot-controller-setup.ps1
```

평소 실행:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\robot-controller-start.ps1
```

더 쉬운 방법:

```text
deployment/windows/setup_robot_controller.bat
deployment/windows/start_robot_controller.bat
```

### Vision PC A/B/C

배포 대상:

```text
GitHub: youngjinsgithub/factory_mes
PowerShell script: deployment/windows/vision-pc-setup.ps1
```

Vision 담당자는 Docker/HMI를 설치하지 않습니다. 자기 위치 스크립트만 실행합니다.

Vision A:

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role A
```

더 쉬운 방법:

```text
deployment/windows/setup_vision_A.bat
deployment/windows/start_vision_A.bat
```

Vision B:

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role B
```

더 쉬운 방법:

```text
deployment/windows/setup_vision_B.bat
deployment/windows/start_vision_B.bat
```

Vision C:

```powershell
mkdir C:\Busan_Project
cd C:\Busan_Project
git clone https://github.com/HeungJAELEE/Busan_Robot.git Indy7_HMI_Clean
cd C:\Busan_Project\Indy7_HMI_Clean
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role C
```

더 쉬운 방법:

```text
deployment/windows/setup_vision_C.bat
deployment/windows/start_vision_C.bat
```

## 4. 업데이트 방식

Robot Controller PC:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
git pull
powershell -ExecutionPolicy Bypass -File .\deployment\windows\robot-controller-setup.ps1
```

Vision PC:

```powershell
cd C:\Busan_Project\Indy7_HMI_Clean
git pull
powershell -ExecutionPolicy Bypass -File .\deployment\windows\vision-pc-setup.ps1 -Role B
```

Vision PC는 자기 위치에 맞춰 `-Role A`, `-Role B`, `-Role C`만 바꾸면 됩니다.

## 5. 운영 원칙

- PLC가 메인 통제권을 가집니다.
- Robot Controller PC는 PLC 출력 `Y160`을 직접 쓰지 않습니다.
- Robot은 물리 배선된 `DI0`을 보고 움직입니다.
- Vision PC는 PLC와만 통신합니다.
- YOLO만 쓰는 작업자는 Vision PC 문서만 보면 됩니다.
- DB는 Robot Controller PC의 MySQL `192.168.3.141`을 기준으로 통합합니다.
