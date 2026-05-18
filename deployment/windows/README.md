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
