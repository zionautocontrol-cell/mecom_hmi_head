# MECOM HMI

간단한 Streamlit 기반 HMI/모니터링 앱과 Modbus RTU 데이터 수집 워커입니다.

## 설치

```powershell
python -m pip install -r requirements.txt
```

## 실행

1. Modbus 수집 워커 시작
```powershell
python modbus_worker.py
```

2. Streamlit 앱 실행
```powershell
streamlit run app.py
```

## Docker 배포

```powershell
docker build -t mecom-hmi .
docker run -p 8501:8501 mecom-hmi
```

## 로그

- 워커 로그: `mecom_hmi.log`

## 기본 구조

- `config.py`: 공통 설정과 경로 정의
- `data_provider.py`: JSON/CSV 읽기/쓰기 로직
- `modbus_worker.py`: PLC/Modbus 데이터 수집
- `app.py`: Streamlit UI
- `realtime_data.json`: 실시간 상태 데이터 저장
- `history_data.csv`: 운전 이력 저장
