# Windows 원클릭 실행 파일

이 폴더는 현장 Windows PC용 실행 파일 모음입니다.

## Robot Controller PC

처음 설치:

```text
setup_robot_controller.bat
```

평소 실행:

```text
start_robot_controller.bat
```

UI만 켜기:

```text
start_hmi_ui.bat
```

UI는 기본적으로 무연결 모드로 켜집니다. 로봇/PLC/MySQL/MQTT는 화면의 연결 버튼이나 서비스 관리 버튼을 눌렀을 때만 붙습니다.

`start_robot_controller.bat`은 Docker 백엔드와 UI를 같이 켭니다. 그래도 실제 로봇 연결은 UI에서 `로봇 통신 연결`을 눌렀을 때 실행되며, Docker Robot Controller의 응답까지 확인한 뒤 연결 성공으로 표시합니다.

GUI가 뜨지 않고 터미널에 `공장 자동화 연속 루프`, `가상 PLC`, `가상 로봇` 로그만 계속 나오면 잘못된 실행 파일을 켠 것입니다. 그 창에서 `Ctrl + C`를 누르고 `start_hmi_ui.bat`을 실행하세요.

## Vision A PC

처음 설치:

```text
setup_vision_A.bat
```

평소 실행:

```text
start_vision_A.bat
```

## Vision B PC

처음 설치:

```text
setup_vision_B.bat
```

평소 실행:

```text
start_vision_B.bat
```

## Vision C PC

처음 설치:

```text
setup_vision_C.bat
```

평소 실행:

```text
start_vision_C.bat
```

Vision PC는 Docker Desktop을 설치하지 않아도 됩니다. Robot Controller PC만 Docker를 사용합니다.
