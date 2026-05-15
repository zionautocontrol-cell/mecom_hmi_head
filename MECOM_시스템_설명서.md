# MECOM HMI 시스템 설명서

> **최종 업데이트:** 2026-05-15  
> **관련 저장소:** `mecom_hmi_head` (현장 HMI), `mecom_head` (본사 통합관제)

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [mecom_hmi_head — 현장 HMI](#3-mecom_hmi_head--현장-hmi)
   - 3.1 [config.py — 전역 설정](#31-configpy--전역-설정)
   - 3.2 [modbus_worker.py — PLC 데이터 수집 엔진](#32-modbus_workerpy--plc-데이터-수집-엔진)
   - 3.3 [api_server.py — 현장 REST API 서버](#33-api_serverpy--현장-rest-api-서버)
   - 3.4 [app.py — Streamlit 사용자 인터페이스](#34-apppy--streamlit-사용자-인터페이스)
   - 3.5 [diagram.html — HMI 시각화](#35-diagramhtml--hmi-시각화)
   - 3.6 [head_client.py — 본사 통신](#36-head_clientpy--본사-통신)
   - 3.7 [data_provider.py — 데이터 영속성 계층](#37-data_providerpy--데이터-영속성-계층)
   - 3.8 [test_plc.py — PLC 진단 도구](#38-test_plcpy--plc-진단-도구)
   - 3.9 [sites/ — 현장별 디렉토리](#39-sites--현장별-디렉토리)
4. [mecom_head — 본사 통합관제](#4-mecom_head--본사-통합관제)
   - 4.1 [config.py — 본사 설정](#41-configpy--본사-설정)
   - 4.2 [api_server.py — 본사 REST API](#42-api_serverpy--본사-rest-api)
   - 4.3 [database.py — SQLite 데이터베이스](#43-databasepy--sqlite-데이터베이스)
   - 4.4 [dashboard.py — 관리자 대시보드](#44-dashboardpy--관리자-대시보드)
5. [PLC 메모리 맵](#5-plc-메모리-맵)
6. [데이터 흐름](#6-데이터-흐름)
7. [알람 시스템](#7-알람-시스템)
8. [설치 및 실행](#8-설치-및-실행)
9. [환경변수 설정](#9-환경변수-설정)
10. [보안](#10-보안)
11. [트러블슈팅](#11-트러블슈팅)

---

## 1. 시스템 개요

MECOM HMI는 **지열 히트펌프 시스템**의 원격 모니터링 및 제어를 위한 통합 관제 시스템입니다. 현장에 설치된 **LS Electric PLC**로부터 Modbus RTU 통신으로 데이터를 수집하여 실시간으로 시각화하고, 이력을 저장하며, 이상 상황 발생 시 알람을 발생시킵니다. 또한 수집된 데이터를 **본사 통합관제 서버**로 전송하여 여러 현장을 중앙에서 관리할 수 있습니다.

### 주요 기능

- **실시간 모니터링:** 히트펌프 15대, 순환펌프 8대, 교반기 3대, 수중펌프 4대의 가동상태를 실시간 애니메이션으로 표시
- **온도/유량 표시:** 8개 온도센서, 2개 유량계, 생산열량을 디지털 값으로 실시간 표시
- **수위 감시:** 4개 집수정의 고수위/저수위 상태 램프 표시
- **데이터 이력:** 1분 간격으로 CSV 파일과 SQLite DB에 자동 저장
- **리포트 생성:** 일일/주간/월간 리포트 PDF 자동 생성 (데스크탑 저장)
- **원격 제어:** 시스템 시동/정지 Modbus Coil 제어
- **알람:** 온도 이상, 유량 이상, 수위 이상, 통신 장애 알람 (로컬 저장 + 본사 전송)
- **본사 연동:** 실시간 데이터, 알람, 일일리포트를 본사 서버로 HTTP 전송
- **현장별 설정:** 배경화면, 다이어그램을 현장별로 커스터마이징

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          현장 (mecom_hmi_head)                          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  PLC (LS XGK/XBC) ←→ Modbus RTU (RS-485, 9600bps)              │  │
│  │    - Discrete Inputs 0~37: 38비트 (히트펌프/펌프/수위 상태)     │  │
│  │    - Holding Registers 0~12: 13워드 (온도/유량/열량)            │  │
│  │    - Coil 0: 시동/정지 제어                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                                    ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  modbus_worker.py (0.5초 간격 무한루프)                         │  │
│  │                                                                   │  │
│  │  1. PLC 데이터 읽기 (비트 38개 + 워드 13개)                      │  │
│  │  2. realtime_data.json 저장 (0.5초)                              │  │
│  │  3. history_data.csv + SQLite 저장 (1분)                         │  │
│  │  4. 알람 평가 → alarm_history.csv                                │  │
│  │  5. head_client.py → 본사 전송                                   │  │
│  │  6. control_command.json 확인 → Coil 제어                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│              ┌─────────────────────┼─────────────────────┐             │
│              ▼                     ▼                     ▼             │
│  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  api_server.py     │  │  head_client.py  │  │  app.py          │  │
│  │  (FastAPI, 8000)   │  │  (HTTP POST)     │  │  (Streamlit, 8501)│  │
│  │                    │  │                  │  │                  │  │
│  │  GET /realtime     │  │  → /api/realtime │  │  감시 / 이력     │  │
│  │  GET /control      │  │  → /api/alarm    │  │  트렌드 / 비번   │  │
│  │  GET /history      │  │  → /api/daily-   │  │                  │  │
│  │  GET /hmi          │  │    report        │  │  diagram.html    │  │
│  └────────────────────┘  └──────────────────┘  │  임베드 +        │  │
│                                               │  1초 갱신         │  │
│                                               └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                            HTTP POST (JSON/CSV)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        본사 (mecom_head)                                │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  api_server.py (FastAPI, 8000)                                  │  │
│  │                                                                   │  │
│  │  POST /api/realtime      → realtime_log 테이블 저장             │  │
│  │  POST /api/alarm         → alarms 테이블 저장                   │  │
│  │  POST /api/daily-report  → daily_reports 테이블 저장            │  │
│  │  GET  /sites             → 현장 목록                             │  │
│  │  GET  /api/alarms        → 알람 조회                             │  │
│  │  GET  /api/realtime-log  → 실시간 데이터 조회                   │  │
│  │  GET  /api/daily-reports → 리포트 조회                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                                    ▼                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  dashboard.py (Streamlit, 8501)                                 │  │
│  │                                                                   │  │
│  │  [탭1] 현장 관리: 등록/삭제/상세조회                              │  │
│  │  [탭2] 알람 이력: 현장별 필터 + 조회                             │  │
│  │  [탭3] 일일리포트: 보고서 목록                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  mecom_head.db (SQLite)                                          │  │
│  │  - sites: 현장 정보                                              │  │
│  │  - realtime_log: 실시간 데이터 로그                              │  │
│  │  - alarms: 알람 이력                                             │  │
│  │  - daily_reports: 일일리포트 CSV (BLOB)                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. mecom_hmi_head — 현장 HMI

### 3.1 `config.py` — 전역 설정

**위치:** `mecom_hmi_head/config.py`

모든 모듈이 공유하는 단일 설정 파일입니다.

#### 현장 식별

| 변수 | 환경변수 | 기본값 | 설명 |
|------|---------|--------|------|
| `SITE_ID` | `MECOM_SITE_ID` | `"default"` | 현장 고유 식별자 |
| `HEAD_ENABLED` | `MECOM_HEAD_ENABLED` | `True` | 본사 통신 활성화 |
| `HEAD_SERVER_URL` | `MECOM_HEAD_SERVER_URL` | `http://localhost:8000` | 본사 서버 주소 |
| `API_KEY` | `MECOM_API_KEY` | `""` | 본사 인증용 API 키 |

#### Modbus 통신

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MODBUS_PORT` | `"com14"` | 시리얼 포트 |
| `MODBUS_BAUDRATE` | `9600` | 통신 속도 |
| `MODBUS_SLAVE_ID` | `1` | PLC 슬레이브 ID |
| `POLL_INTERVAL` | `0.5` | 데이터 읽기 간격(초) |
| `BIT_READ_START` | `0` | 비트 읽기 시작 주소 |
| `WORD_READ_START` | `0` | 워드 읽기 시작 주소 |
| `COIL_ADDRESS` | `1` | 제어용 Coil 주소 (1-indexed) |
| `CONTROL_ENABLED` | `True` | 원격 제어 활성화 |

#### 파일 경로

| 변수 | 경로 | 설명 |
|------|------|------|
| `REALTIME_JSON` | `{BASE_DIR}/realtime_data.json` | 실시간 데이터 (0.5초 갱신) |
| `HISTORY_CSV` | `{BASE_DIR}/history_data.csv` | 분당 이력 CSV |
| `SITE_DIR` | `{BASE_DIR}/sites/{SITE_ID}` | 현장별 디렉토리 |
| `DIAGRAM_HTML` | `{SITE_DIR}/diagram.html` | 현장별 HMI 화면 |
| `BACKGROUND_IMAGE` | `{SITE_DIR}/background.png` | 현장별 배경화면 |
| `LOG_FILE` | `{BASE_DIR}/mecom_hmi.log` | 로그 파일 |
| `CONTROL_COMMAND_JSON` | `{BASE_DIR}/control_command.json` | 제어 명령 |
| `DB_PATH` | `{BASE_DIR}/mecom_data.db` | SQLite DB |
| `PASSWORD_FILE` | `{BASE_DIR}/password.json` | 관리자 비밀번호 |

#### 히스토리 컬럼 (13개)

| # | 컬럼명 | 설명 | 단위 | 워드 인덱스 |
|---|--------|------|------|-----------|
| 0 | `날짜` | `YY/MM/DD HH:MM` 형식 타임스탬프 | - | - |
| 1 | `지중공급온도(1동)` | 1동 지중 공급 온도 | °C | W0 |
| 2 | `지중환수온도(1동)` | 1동 지중 환수 온도 | °C | W1 |
| 3 | `지중공급온도(2동)` | 2동 지중 공급 온도 | °C | W2 |
| 4 | `지중환수온도(2동)` | 2동 지중 환수 온도 | °C | W3 |
| 5 | `2차공급온도(1동)` | 1동 2차 측 공급 온도 | °C | W4 |
| 6 | `2차환수온도(1동)` | 1동 2차 측 환수 온도 | °C | W5 |
| 7 | `2차공급온도(2동)` | 2동 2차 측 공급 온도 | °C | W6 |
| 8 | `2차환수온도(2동)` | 2동 2차 측 환수 온도 | °C | W7 |
| 9 | `1동유량` | 1동 유량 | m³/h | W8 |
| 10 | `2동유량` | 2동 유량 | m³/h | W9 |
| 11 | `생산열량` | 순시 생산 열량 | kW | W10 |
| 12 | `누적열량` | 누적 생산 열량 | kWh | W11+W12(32비트) |

---

### 3.2 `modbus_worker.py` — PLC 데이터 수집 엔진

**위치:** `mecom_hmi_head/modbus_worker.py`  
**실행:** `python modbus_worker.py` (백그라운드 프로세스)

#### 주요 함수

| 함수 | 설명 |
|------|------|
| `create_modbus_client()` | ModbusSerialClient 생성 (port, baudrate, timeout=1, 8N1) |
| `_modbus_read_call(client, method, address, count)` | slave 파라미터 유/무 모두 시도하는 제네릭 래퍼 |
| `process_control_request(client, control)` | 시동/정지 명령 → `write_coil()` 실행 |
| `main()` | 무한 루프 — 전체 데이터 수집 주기 |

#### `main()` 0.5초 루프 상세

```
1. 명령 처리 (최우선)
   └─ control_command.json 확인 → "requested" 상태면 Coil write 실행

2. 연결 확인
   └─ 미연결 시 client.connect() 시도

3. PLC 데이터 읽기
   ├─ read_discrete_inputs(address=0, count=38) → 38비트
   │  ※ Coil 폴백 없음 (CHANGELOG 문제3 해결: 폴백 시 다른 주소 읽힘)
   └─ read_holding_registers(address=0, count=13) → 13워드
      └─ 실패 시 read_input_registers 폴백
      └─ 13개도 실패 시 count=11 폴백

4. 데이터 가공
   ├─ bits[0:38] → current_data["bits"]
   ├─ registers[i] ÷ 10.0 → words[i] (PLC 10배 스케일 보정)
   └─ (registers[12] << 16) | registers[11] → accum_heat (32비트)

5. 상태 갱신
   ├─ 성공 → status="connected", last_valid_data 갱신
   └─ 실패 → status="disconnected", last_valid_data 유지

6. realtime_data.json 저장 (원자적 쓰기: .tmp → rename)

7. head_send_realtime() → 본사 전송 (매 사이클)

8. 분당 이력
   ├─ append_history_row() → history_data.csv
   └─ save_history_to_db() → mecom_data.db (SQLite)

9. 알람 평가
   ├─ evaluate_alarms() → alarm 평가
   ├─ append_alarm_history() → alarm_history.csv
   └─ head_send_alarm() → 본사 전송 (알람별)

10. 일일리포트 전송
    └─ 날짜 변경 + 01:00 이후 → head_send_daily_report()

11. time.sleep(POLL_INTERVAL) = 0.5초
```

#### 제어 명령 처리 흐름

```
app.py [시작] 버튼 클릭
  → save_control_command(command="start", status="requested")
  → control_command.json 파일 기록
  → modbus_worker.py 감지 (0.5초 내)
  → process_control_request()
    → write_coil(address=COIL_ADDRESS-1, value=True)
    → 성공: status="executed", message="시스템 운전중"
    → 실패: status="failed", message="Modbus write failed"
```

---

### 3.3 `api_server.py` — 현장 REST API 서버

**위치:** `mecom_hmi_head/api_server.py`  
**실행:** `python api_server.py` (백그라운드, 포트 8000)  
**기반:** FastAPI

#### 엔드포인트

| 메서드 | 경로 | 응답 | 설명 |
|--------|------|------|------|
| `GET` | `/realtime` | JSON | `realtime_data.json` 통째로 반환 |
| `GET` | `/control` | JSON | `control_command.json` 반환 |
| `GET` | `/history?limit=N` | JSON | SQLite history_logs 조회 |
| `GET` | `/hmi` | HTML | **diagram.html + 실시간 데이터 치환** |

#### `GET /hmi` — HMI HTML 렌더링 (핵심)

```
1. realtime_data.json 로드
2. sites/{SITE_ID}/diagram.html 읽기
3. 배경화면 존재 시 base64 인코딩 → {{BACKGROUND_IMAGE}} 치환
4. 비트 치환 ({{B0}}~{{B37}}):
   - bits[i]=True,  i<30 → class="running"
   - bits[i]=False, i<30 → class="paused"
   - bits[i]=True,  i>=30 → class="on"
   - bits[i]=False, i>=30 → class="off"
5. 워드 치환 ({{W0}}~{{W10}}):
   - words[i] → f"{value:.1f}"
6. Cache-Control: no-cache 헤더와 함께 HTML 반환
```

#### 자동 일일리포트 (APScheduler cron)

```python
scheduler.add_job(_auto_daily_report, "cron", hour=1, minute=0)
```

`_auto_daily_report()` 동작:
1. 전날(어제 00:00~23:59) 데이터를 history_data.csv에서 필터링
2. 10분 평균으로 리샘플링
3. FPDF로 가로 A4 PDF 생성 (Nanum 폰트 = malgun.ttf)
4. `Desktop/리포트/일일리포트/`에 저장
5. `head_send_daily_report()` → 본사로 CSV 전송

---

### 3.4 `app.py` — Streamlit 사용자 인터페이스

**위치:** `mecom_hmi_head/app.py`  
**실행:** `streamlit run app.py` (포트 8501)  
**접속:** `http://localhost:8501`

#### 페이지 구조

| 메뉴 | 페이지 함수 | 설명 |
|------|-----------|------|
| 📡 **감시** | `render_hmi_dashboard()` | HMI 다이어그램 iframe 임베드 (1시간 캐싱) |
| 📈 **이력** | `render_history_page()` | 운전이력 테이블 + 리포트 생성/다운로드 |
| 📊 **트렌드** | `render_trend_page()` | 항목 선택형 라인차트 |
| 🔑 **비밀번호 변경** | `render_password_page()` | 관리자 비밀번호 변경 |

#### 사이드바 제어

```
[시작] 버튼 → control_command.json: command="start", status="requested"
[정지] 버튼 → control_command.json: command="stop",  status="requested"

실시간 메트릭:
  - 순시 열량 (kW): words[10]
  - 누적 열량 (kW/h): accum_heat
```

#### 중요 구현 상세

- **`_get_hmi_html()`**: `@st.cache_data(ttl=3600)` — 1시간 캐싱. 과거 iframe src= 방식의 30초 프리징 문제 해결
- **`components.html(html, height=700)`**: 인라인 HTML 삽입으로 재생성 비용 최소화
- **`st_autorefresh(interval=120000)`**: 2분 간격 페이지 갱신 (감시화면은 JS 1초 폴링과 별개)

#### 리포트 종류

| 유형 | 버튼 | 기간 | 리샘플링 옵션 |
|------|------|------|--------------|
| 일일 | 📅 일일 리포트 | 오늘 00:00~현재 | 1분, 10분, 30분, 1시간 |
| 주간 | 📆 주간 리포트 | 최근 7일 | 10분, 30분, 1시간, 1일 |
| 월간 | 📆 월간 리포트 | 최근 30일 | 1시간, 1일 |
| 사용자 지정 | 📅 사용자 지정 | 시작일~종료일 설정 | 1분~1일 |

---

### 3.5 `diagram.html` — HMI 시각화

**위치:** `mecom_hmi_head/sites/{SITE_ID}/diagram.html`  
**구성:** CSS 244줄 + HTML 120줄 + JavaScript 92줄 = 총 468줄

#### 화면 구성 (16:9 비율)

```
┌─────────────────────────────────────────────────────────────┐
│  [실시간 시계]                                    ZONE 2   │
│                                                             │
│  [HP08][HP09][HP10][HP11][HP12][HP13][HP14]                 │
│  [CP19]  [CP20]  [CP21]  [CP22]                             │
│              [지중공급:W2°C]  [지중환수:W3°C]              │
│              [2차공급:W6°C] [유량:W9] [2차환수:W7°C]       │
│                                                             │
│  ─────────────────────────────────────────────────────      │
│                                                             │
│  [HP00][HP01][HP02][HP03][HP04][HP05][HP06]                 │
│  [CP15]  [CP16]  [CP17]  [CP18]             ZONE 1          │
│              [지중공급:W0°C]  [지중환수:W1°C]              │
│              [2차공급:W4°C] [유량:W8] [2차환수:W5°C]       │
│                                                             │
│  [교반기]  [교반기]  [교반기]  [수중펌프×4]  [수위램프×8] │
│   B23       B24       B25      B26~B29         B30~B37      │
└─────────────────────────────────────────────────────────────┘
```

#### 장비별 시각화 스타일

| 장비 | CSS 클래스 | 개수 | 비트 인덱스 | 색상 | 회전 속도 | 크기 |
|------|-----------|------|------------|------|----------|------|
| 히트펌프 (1동) | `hp-fan` | 7 | B0~B6 | 주황 | 1.0초 | 3.5% |
| 히트펌프 (2동) | `hp-fan` | 8 | B7~B14 | 주황 | 1.0초 | 3.5% |
| 순환펌프 (1동) | `cp-impeller` | 4 | B15~B18 | 빨강 | 0.6초 | 2.5% |
| 순환펌프 (2동) | `cp-impeller` | 4 | B19~B22 | 빨강 | 0.6초 | 2.5% |
| 교반기 | `cp-impeller` | 3 | B23~B25 | 빨강 | 0.6초 | 2.5% |
| 수중펌프 | `sub-pump` | 4 | B26~B29 | 파랑 | 0.6초 | 2.5% |
| 수위센서 | `level-lamp` | 8 | B30~B37 | 적색 | - | 0.7vw |

#### JavaScript 동작

| 함수 | 실행 주기 | 설명 |
|------|----------|------|
| `updateClock()` | 1초 | `YYYY/MM/DD (Day) HH:MM:SS` 포맷 시계 갱신 |
| `pollData()` | 1초 | XHR GET `/realtime?_={timestamp}` → JSON 파싱 |
| `applyData(data)` | 1초 | bits 변화 감지 후 DOM 업데이트, words 전체 업데이트 |
| `applyBitChange(i, val)` | 변경 시 | 비트 `<30`: `running`/`paused` 토글, `>=30`: `on`/`off` 토글 |
| `updateWordUI(i, val)` | 1초 | `data-word` 속성 기준 요소 찾아 `value.toFixed(1) + unit` 표시 |

`bitApplied[]` 배열로 이전 상태를 추적하여 **변경된 비트만 DOM 조작**하여 불필요한 DOM 업데이트를 방지합니다.

---

### 3.6 `head_client.py` — 본사 통신

**위치:** `mecom_hmi_head/head_client.py`

#### 전송 함수

| 함수 | 엔드포인트 | 데이터 형식 | 전송 내용 | 빈도 |
|------|-----------|-----------|----------|------|
| `send_realtime()` | `/api/realtime` | JSON | site_id, timestamp, status, bits[:38], words[:11], accum_heat | 매 0.5초 |
| `send_alarm()` | `/api/alarm` | JSON | site_id, alarm_type, alarm_id, message, severity, value, timestamp | 알람 발생 시 |
| `send_daily_report()` | `/api/daily-report` | Multipart | history_data.csv 파일 | 매일 01:00+ |

#### 알람 중복 방지

```python
_previous_alarms: set = set()  # 모듈 전역

def send_alarm(...):
    key = (alarm_type, alarm_id)
    if key in _previous_alarms:
        return False  # 이미 전송된 알람 Skip
    _previous_alarms.add(key)
    # ... HTTP POST ...
```

#### 공통 헤더

```
X-Site-ID: {SITE_ID}
X-API-Key: {API_KEY}
```

---

### 3.7 `data_provider.py` — 데이터 영속성 계층

**위치:** `mecom_hmi_head/data_provider.py`

#### JSON 파일 I/O

| 함수 | 파일 | 설명 |
|------|------|------|
| `load_realtime_data()` | `realtime_data.json` | JSON 읽기 + 필드 검증 + 마지막값 캐싱 |
| `save_realtime_data(data)` | `realtime_data.json` | 원자적 쓰기 (.tmp → Path.replace) |
| `load_control_command()` | `control_command.json` | 기본값과 병합하여 로드 |
| `save_control_command(...)` | `control_command.json` | 선택적 필드 업데이트 |

#### CSV 파일 I/O

| 함수 | 파일 | 설명 |
|------|------|------|
| `append_history_row(values, accum, ts)` | `history_data.csv` | 11개 값 + 누적열량 추가 |
| `load_history_data()` | `history_data.csv` | pandas DataFrame 반환 |
| `append_alarm_history(alarms)` | `alarm_history.csv` | 알람 CSV 추가 |
| `load_alarm_history()` | `alarm_history.csv` | pandas DataFrame 반환 |

#### SQLite DB I/O

| 함수 | 테이블 | 설명 |
|------|--------|------|
| `init_db()` | `realtime_logs`, `history_logs` | 테이블 생성 (시작 시 1회) |
| `save_history_to_db(words, accum)` | `history_logs` | 11개 워드 + 누적열량 INSERT |

#### 알람 평가 (`evaluate_alarms()`)

```
입력: current_data = {status, timestamp, bits[38], words[11], accum_heat}

1. 연결 알람:
   status != "connected" → alarm_id="PLC_CONN", severity="high"

2. 비트 알람 (bits 30~37):
   각 비트가 True면 해당 수위 알람 발생
   B30=집수정1고수위, B31=집수정1저수위, ... B37=집수정4저수위
   severity = "high"

3. 값 알람 (words 0~7, 8, 10):
   각 워드별 min/max 임계값 초과 시 알람
   ┌─────────────┬──────┬──────┬──────────┐
   │ 항목        │ 최소  │ 최대  │ 심각도   │
   ├─────────────┼──────┼──────┼──────────┤
   │ 온도(W0~W7) │ 5.0  │ 45.0 │ medium   │
   │ 유량(W8)    │ 1.0  │ 120.0│ high     │
   │ 생산열량(W10)│ 0.0  │ 1000.0│ medium  │
   └─────────────┴──────┴──────┴──────────┘
```

---

### 3.8 `test_plc.py` — PLC 진단 도구

**위치:** `mecom_hmi_head/test_plc.py`  
**실행:** `python test_plc.py`

#### 4단계 테스트

| 단계 | 내용 | 기대 결과 |
|------|------|----------|
| 1 | COM 포트 스캔 + 설정 포트 확인 | `Found configured port: COM14` |
| 2 | Modbus 연결 시도 | `Connected successfully` |
| 3 | 38비트 + 13워드 읽기 | `Bits[0:16]=1010...`, `Words[0:3]=[12.5, 8.3, ...]` |
| 4 | 연결 종료 | `Connection closed` |

---

### 3.9 `sites/` — 현장별 디렉토리

**위치:** `mecom_hmi_head/sites/`

#### 디렉토리 구조

```
sites/
├── default/              # 기본 현장
│   ├── diagram.html      # HMI 화면 HTML (config.py DIAGRAM_HTML)
│   └── background.png    # 배경화면 1920×1080 (config.py BACKGROUND_IMAGE)
├── template/             # 신규 현장 템플릿
│   └── diagram.html      # 복제용 원본
└── setup_site.py         # 현장 생성 CLI 도구
```

#### `setup_site.py` 사용법

```bash
# site_a 현장 생성
python sites/setup_site.py site_a --name "A현장"

# 출력 예시
#   Copied: diagram.html
#   Created background: background.png (1920x1080)
#   Site 'site_a' created at: .../sites/site_a
#   Next steps:
#     1. Replace .../sites/site_a/background.png with actual image
#     2. Set SITE_ID='site_a' via env MECOM_SITE_ID
```

---

## 4. mecom_head — 본사 통합관제

### 4.1 `config.py` — 본사 설정

**위치:** `mecom_head/config.py`

| 변수 | 환경변수 | 기본값 | 설명 |
|------|---------|--------|------|
| `DB_PATH` | - | `BASE_DIR/mecom_head.db` | SQLite DB 파일 경로 |
| `HOST` | `MECOM_HEAD_HOST` | `0.0.0.0` | 바인딩 주소 |
| `PORT` | `MECOM_HEAD_PORT` | `8000` | 서비스 포트 |
| `TRUSTED_API_KEYS` | `MECOM_TRUSTED_KEYS` | `{}` | 현장 API 키 딕셔너리 |
| `ADMIN_USERNAME` | `MECOM_ADMIN_USER` | `admin` | 대시보드 관리자 ID |
| `ADMIN_PASSWORD` | `MECOM_ADMIN_PASS` | `admin123` | 대시보드 관리자 비밀번호 |

#### API 키 설정 예시

```bash
# 환경변수로 설정
set MECOM_TRUSTED_KEYS=site_a=abc123,site_b=def456

# 파싱 결과
TRUSTED_API_KEYS = {"site_a": "abc123", "site_b": "def456"}

# 미설정 시 → {} (빈 딕셔너리) → 모든 요청 허용 (오픈 모드)
```

---

### 4.2 `api_server.py` — 본사 REST API

**위치:** `mecom_head/api_server.py`  
**실행:** `python api_server.py` (포트 8000)

#### 인증 시스템

**`verify_request(request)` — 현장 인증:**
```
1. X-Site-ID 헤더 확인 → 없으면 400 Bad Request
2. TRUSTED_API_KEYS가 비어있으면 → 인증 생략 (오픈 모드)
3. TRUSTED_API_KEYS[site_id] 조회 → 값이 있으면 X-API-Key와 비교
4. 불일치 시 403 Forbidden
```

**`verify_admin(request)` — 관리자 인증:**
```
1. Authorization: Bearer {json} 헤더 확인
2. JSON 디코드: {"user": ..., "pass": ...}
3. ADMIN_USERNAME/ADMIN_PASSWORD와 비교
※ 현재 모든 엔드포인트에서 verify_admin() 미사용
```

#### 전체 API 목록

##### 현장 관리

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `GET` | `/` | 없음 | 서버 상태 + 버전 정보 |
| `GET` | `/sites` | 없음 | 전체 현장 목록 |
| `GET` | `/sites/{site_id}` | 없음 | 특정 현장 상세 정보 |
| `POST` | `/api/register?site_id=&name=&api_key=` | API key (부분) | 현장 등록 |
| `DELETE` | `/api/sites/{site_id}` | 없음 | 현장 삭제 |
| `PUT` | `/api/sites/{site_id}` | 없음 | 현장 정보 수정 |

##### 데이터 수신 (현장 → 본사)

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `POST` | `/api/daily-report` | `verify_request` | CSV 파일 수신 → daily_reports 테이블 |
| `POST` | `/api/alarm` | `verify_request` | JSON 알람 수신 → alarms 테이블 |
| `POST` | `/api/realtime` | `verify_request` | JSON 실시간 데이터 수신 → realtime_log 테이블 |

##### 데이터 조회

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| `GET` | `/api/alarms?site_id=&limit=N` | 없음 | 알람 이력 조회 |
| `GET` | `/api/realtime-log?site_id=&limit=N` | 없음 | 실시간 로그 조회 |
| `GET` | `/api/daily-reports?site_id=&limit=N` | 없음 | 일일리포트 메타데이터 조회 |
| `GET` | `/api/health` | 없음 | 서버 상태 체크 |

##### 현장 자동 등록

모든 데이터 수신 API(`/api/realtime`, `/api/alarm`, `/api/daily-report`)는 데이터 저장 후 `register_site(site_id)`를 호출합니다. 즉, 현장이 최초로 데이터를 전송하면 **자동으로 sites 테이블에 등록**됩니다.

---

### 4.3 `database.py` — SQLite 데이터베이스

**위치:** `mecom_head/database.py`

#### 테이블 스키마

##### `sites` — 현장 정보

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| `id` | TEXT | PRIMARY KEY | 현장 식별자 |
| `name` | TEXT | NOT NULL | 현장명 |
| `api_key` | TEXT | NOT NULL DEFAULT '' | API 키 |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | 등록일시 |

##### `daily_reports` — 일일리포트

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 보고서 ID |
| `site_id` | TEXT | NOT NULL REFERENCES sites(id) | 현장 ID |
| `report_date` | TEXT | NOT NULL | 보고서 기준일 |
| `csv_data` | BLOB | | CSV 파일 원본 (바이너리) |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | 수신일시 |

##### `alarms` — 알람 이력

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 알람 ID |
| `site_id` | TEXT | NOT NULL REFERENCES sites(id) | 현장 ID |
| `alarm_type` | TEXT | NOT NULL | "connection" / "bit" / "value" |
| `alarm_id` | TEXT | NOT NULL | "PLC_CONN" / "BIT30" / "WORD0" 등 |
| `message` | TEXT | NOT NULL | 한글 알람 메시지 |
| `severity` | TEXT | NOT NULL | "high" / "medium" |
| `value` | REAL | | 관련 수치값 |
| `timestamp` | TEXT | NOT NULL | 알람 발생시간 |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | DB 기록시간 |

##### `realtime_log` — 실시간 데이터 로그

| 컬럼 | 타입 | 제약조건 | 설명 |
|------|------|---------|------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 로그 ID |
| `site_id` | TEXT | NOT NULL | 현장 ID |
| `timestamp` | TEXT | NOT NULL | 데이터 수집시간 |
| `status` | TEXT | NOT NULL DEFAULT 'disconnected' | 연결 상태 |
| `bits_json` | TEXT | | 38비트 JSON 문자열 |
| `words_json` | TEXT | | 11워드 JSON 문자열 |
| `accum_heat` | REAL | DEFAULT 0 | 누적열량 |
| `created_at` | TEXT | NOT NULL DEFAULT (datetime('now')) | DB 기록시간 |

#### 주요 DB 함수

| 함수 | SQL | 설명 |
|------|-----|------|
| `register_site(id, name, key)` | `INSERT OR IGNORE INTO sites` | 현장 등록 (중복 무시) |
| `get_site(id)` | `SELECT * FROM sites WHERE id=?` | 현장 조회 |
| `get_sites()` | `SELECT * FROM sites ORDER BY name` | 전체 현장 목록 |
| `update_site(id, name, key)` | `UPDATE sites SET ... WHERE id=?` | 현장 정보 수정 (COALESCE 패턴) |
| `delete_site(id)` | `DELETE FROM sites WHERE id=?` | 현장 삭제 |
| `save_daily_report(...)` | `INSERT INTO daily_reports` | 일일리포트 저장 (BLOB 포함) |
| `get_daily_reports(site, limit)` | `SELECT id,site_id,report_date,created_at ...` | 보고서 메타데이터만 조회 (BLOB 제외) |
| `save_alarm(...)` | `INSERT INTO alarms` | 알람 저장 |
| `get_alarms(site, limit)` | `SELECT * FROM alarms [WHERE site_id=] ORDER BY id DESC LIMIT ?` | 알람 조회 |
| `save_realtime(...)` | `INSERT INTO realtime_log` | 실시간 데이터 저장 |
| `get_recent_realtime(site, limit)` | `SELECT * FROM realtime_log WHERE site_id=? ORDER BY id DESC LIMIT ?` | 최근 실시간 데이터 |

---

### 4.4 `dashboard.py` — 관리자 대시보드

**위치:** `mecom_head/dashboard.py`  
**실행:** `streamlit run dashboard.py` (포트 8501)

#### 로그인

```
계정: admin / admin123 (환경변수로 변경 가능)
인증 방식: Streamlit session_state에 {"user": ..., "pass": ...} 저장
```

#### 탭 1: 현장 관리

**좌측 (60%) — 등록 현장 목록:**
- 각 현장: 이름, ID, API 키, 생성일자 표시
- `[상세]` 버튼 → 실시간 로그 DataFrame + 센서값 JSON
- `[삭제]` 버튼 → DELETE /api/sites/{id}

**우측 (40%) — 현장 등록:**
- Site ID, Site Name, API Key 입력 폼
- 등록 버튼 → POST /api/register

#### 탭 2: 알람 이력

- 현장 필터 (전체 / 개별)
- 조회 개수 설정 (10~200)
- 알람 DataFrame 표시

#### 탭 3: 일일리포트

- 현장 필터
- 보고서 메타데이터 DataFrame 표시

---

## 5. PLC 메모리 맵

### 데이터 영역

| Modbus 주소 | PLC 주소 | 기능 코드 | 개수 | 내용 |
|------------|---------|----------|------|------|
| 0~6 (B0~B6) | 10001~10007 | FC02 (Discrete Input) | 7 | 1동 히트펌프 가동상태 |
| 7~14 (B7~B14) | 10008~10015 | FC02 | 8 | 2동 히트펌프 가동상태 |
| 15~18 (B15~B18) | 10016~10019 | FC02 | 4 | 1동 순환펌프 가동상태 |
| 19~22 (B19~B22) | 10020~10023 | FC02 | 4 | 2동 순환펌프 가동상태 |
| 23~25 (B23~B25) | 10024~10026 | FC02 | 3 | 교반기 가동상태 |
| 26~29 (B26~B29) | 10027~10030 | FC02 | 4 | 수중펌프 가동상태 |
| 30 (B30) | 10031 | FC02 | 1 | 집수정1 고수위 |
| 31 (B31) | 10032 | FC02 | 1 | 집수정1 저수위 |
| 32 (B32) | 10033 | FC02 | 1 | 집수정2 고수위 |
| 33 (B33) | 10034 | FC02 | 1 | 집수정2 저수위 |
| 34 (B34) | 10035 | FC02 | 1 | 집수정3 고수위 |
| 35 (B35) | 10036 | FC02 | 1 | 집수정3 저수위 |
| 36 (B36) | 10037 | FC02 | 1 | 집수정4 고수위 |
| 37 (B37) | 10038 | FC02 | 1 | 집수정4 저수위 |

### 아날로그 영역

| Modbus 주소 | PLC 주소 | 기능 코드 | 스케일 | 내용 |
|------------|---------|----------|--------|------|
| 0 (W0) | 40001 | FC03 (Holding Register) | ÷10 | 지중공급온도(1동) |
| 1 (W1) | 40002 | FC03 | ÷10 | 지중환수온도(1동) |
| 2 (W2) | 40003 | FC03 | ÷10 | 지중공급온도(2동) |
| 3 (W3) | 40004 | FC03 | ÷10 | 지중환수온도(2동) |
| 4 (W4) | 40005 | FC03 | ÷10 | 2차공급온도(1동) |
| 5 (W5) | 40006 | FC03 | ÷10 | 2차환수온도(1동) |
| 6 (W6) | 40007 | FC03 | ÷10 | 2차공급온도(2동) |
| 7 (W7) | 40008 | FC03 | ÷10 | 2차환수온도(2동) |
| 8 (W8) | 40009 | FC03 | ÷10 | 1동유량 |
| 9 (W9) | 40010 | FC03 | ÷10 | 2동유량 |
| 10 (W10) | 40011 | FC03 | ÷10 | 생산열량 |
| 11 (W11) | 40012 | FC03 | - | 누적열량 하위워드 |
| 12 (W12) | 40013 | FC03 | - | 누적열량 상위워드 |

### 제어 영역

| Modbus 주소 | PLC 주소 | 기능 코드 | 설명 |
|------------|---------|----------|------|
| 0 | 00001 | FC05 (Write Single Coil) | True=시동, False=정지 |

---

## 6. 데이터 흐름

### 6.1 정상 운전 시

```
[PLC] --RS-485--> [modbus_worker.py] --0.5초-->
  │
  ├── realtime_data.json ──GET── [api_server.py] ──GET── [diagram.html JS] (1초 폴링)
  │                                              └──GET── [app.py] (1시간 캐싱)
  │
  ├── history_data.csv (1분) ──> [api_server.py _auto_daily_report] (01:00)→ PDF
  │
  ├── mecom_data.db (1분)
  │
  └── head_client.py ──HTTP POST──> [mecom_head api_server.py]
       ├── /api/realtime (0.5초) → realtime_log 테이블
       ├── /api/alarm (알람시)    → alarms 테이블
       └── /api/daily-report (01:00) → daily_reports 테이블
```

### 6.2 통신 장애 시

```
PLC 읽기 실패
  → status = "disconnected"
  → bits/words = last_valid_data 유지 (화면 깜빡임 방지)
  → realtime_data.json에 disconnected 상태 저장
  → head_send_realtime() → 본사에 "disconnected" 전송
  → evaluate_alarms() → PLC_CONN 알람 발생
    → alarm_history.csv 기록
    → head_send_alarm()으로 본사 전송
```

### 6.3 제어 명령 시

```
app.py [시작/정지] 버튼
  → control_command.json: command="start"/"stop", status="requested"
  → modbus_worker.py (0.5초 루프에서 감지)
    → process_control_request()
    → write_coil(address=0, value=True/False)
    → 성공→status="executed", 실패→status="failed"
```

---

## 7. 알람 시스템

### 알람 유형

| 유형 | 알람 ID | 조건 | 심각도 |
|------|---------|------|--------|
| 연결 장애 | `PLC_CONN` | status != "connected" | high |
| 수위 이상 | `BIT30`~`BIT37` | bits[30]~bits[37] == True | high |
| 온도 저/고 | `WORD0`~`WORD7` | words[i] < 5.0 또는 > 45.0 | medium |
| 유량 저/고 | `WORD8` | words[8] < 1.0 또는 > 120.0 | high |
| 생산열량 이상 | `WORD10` | words[10] < 0.0 또는 > 1000.0 | medium |

### 알람 전파 경로

```
evaluate_alarms() → 악 0.5초마다 실행
  │
  ├── CSV 기록: alarm_history.csv (분당 1회, 중복 방지)
  │
  └── 본사 전송: head_send_alarm() (중복 방지: _previous_alarms set)
       └── HTTP POST → mecom_head /api/alarm → alarms 테이블
```

---

## 8. 설치 및 실행

### 8.1 수동 설치

```bash
# 1. Python 패키지 설치
pip install -r requirements.txt

# 2. 실행 (3개 프로세스)
python modbus_worker.py          # 터미널 1: PLC 데이터 수집
python api_server.py             # 터미널 2: REST API (포트 8000)
streamlit run app.py             # 터미널 3: 웹 UI (포트 8501)
```

### 8.2 배치 파일 실행

```bash
# start_hmi.bat: 3개 프로세스를 한 번에 실행
start_hmi.bat
```

### 8.3 설치 프로그램

```bash
# Windows 설치 마법사
install.bat    # Batch 버전
install.ps1    # PowerShell 버전
```

`install.bat`이 수행하는 작업:
1. Python 설치 확인
2. pip 패키지 설치
3. 이전 데이터(realtime JSON, CSV, DB, 로그) 초기화
4. COM 포트 설정 (숫자만 입력해도 자동 "COM" prefix)
5. 현장 ID, 본사 서버 주소, API 키 설정
6. 데스크탑 바로가기 생성

### 8.4 Docker 배포

```bash
docker build -t mecom-hmi .
docker run -p 8501:8501 mecom-hmi
```

### 8.5 본사 서버 실행

```bash
cd mecom_head

# API 서버 실행
python api_server.py  # 포트 8000

# 대시보드 실행 (별도 터미널)
streamlit run dashboard.py  # 포트 8501
```

---

## 9. 환경변수 설정

### mecom_hmi_head (현장)

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `MECOM_SITE_ID` | `"default"` | 현장 식별자 |
| `MECOM_HEAD_ENABLED` | `"true"` | 본사 통신 활성화 |
| `MECOM_HEAD_SERVER_URL` | `"http://localhost:8000"` | 본사 서버 주소 |
| `MECOM_API_KEY` | `""` | 본사 인증용 API 키 |

### mecom_head (본사)

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `MECOM_HEAD_HOST` | `"0.0.0.0"` | 바인딩 주소 |
| `MECOM_HEAD_PORT` | `8000` | 서비스 포트 |
| `MECOM_TRUSTED_KEYS` | `""` | 현장별 API 키 (site_a=key1,site_b=key2) |
| `MECOM_ADMIN_USER` | `"admin"` | 대시보드 관리자 ID |
| `MECOM_ADMIN_PASS` | `"admin123"` | 대시보드 관리자 비밀번호 |
| `MECOM_HEAD_API` | `"http://localhost:8000"` | 대시보드가 접속할 API 주소 |

### 설정 예시

```bash
# 현장 (mecom_hmi_head)
set MECOM_SITE_ID=site_a
set MECOM_HEAD_SERVER_URL=http://192.168.0.100:8000
set MECOM_API_KEY=abc123

# 본사 (mecom_head)
set MECOM_TRUSTED_KEYS=site_a=abc123,site_b=def456
set MECOM_ADMIN_PASS=secure_password
```

---

## 10. 보안

### 현재 보안 상태

| 항목 | 상태 | 권장 조치 |
|------|------|----------|
| 현장→본사 API 인증 | 환경변수로 API 키 설정 가능, 미설정시 무인증 | `MECOM_TRUSTED_KEYS` 설정 |
| 본사 조회 API | 인증 없음 (전체 공개) | VPN/방화벽으로 접근 제한 |
| 관리자 대시보드 | Streamlit 로그인 (고정 Bearer 토큰) | 환경변수로 비밀번호 변경 |
| 현장 대시보드 | 정적 비밀번호 "1234" | app.py에서 비밀번호 변경 기능 사용 |
| Modbus 통신 | 평문 (RS-485, 암호화 없음) | 물리적 보안 |

### 권장 보안 설정

```bash
# 본사: API 키 설정
set MECOM_TRUSTED_KEYS=site_a=K3yF0rS1t3A,site_b=An07h3rK3y

# 본사: 관리자 비밀번호 변경
set MECOM_ADMIN_PASS=Str0ng!P@ssw0rd

# 현장: API 키 설정
set MECOM_API_KEY=K3yF0rS1t3A
```

---

## 11. 트러블슈팅

### 문제 1: PLC 통신 안 됨

```
증상: realtime_data.json status = "disconnected"
로그: mecom_hmi.log 확인

점검:
1. python test_plc.py 실행
2. COM 포트 번호 확인 (config.py MODBUS_PORT)
3. PLC 전원 확인
4. RS-485 케이블 연결 확인
5. PLC Modbus 설정 확인 (슬레이브 ID, 통신속도)
```

### 문제 2: 화면 멈춤/프리징

```
원인: iframe src= 방식으로 매 30초 HTTP 요청
현재: @st.cache_data(ttl=3600)으로 1시간 캐싱 + components.html 인라인 삽입

점검:
1. api_server.py (포트 8000) 실행 중인지 확인
2. http://localhost:8000/hmi 직접 접속해보기
3. Streamlit 캐시 초기화: streamlit cache clear
```

### 문제 3: HP 가동상태 깜빡임

```
원인: read_discrete_inputs 실패 시 read_coils 폴백 → 다른 주소 영역 읽힘
해결: coil 폴백 완전 제거, read_discrete_inputs만 사용

점검:
1. mecom_hmi.log에서 "trying coil fallback" 메시지 확인
2. PLC Modbus 통신 안정성 확인
```

### 문제 4: 본사 데이터 미전송

```
점검:
1. mecom_hmi_head config.py HEAD_ENABLED = True 확인
2. mecom_hmi_head config.py HEAD_SERVER_URL 정확한 주소 확인
3. mecom_head api_server.py 실행 중인지 확인
4. 본사 서버 방화벽 확인 (포트 8000)
5. mecom_hmi_head 로그에서 "sent successfully" 메시지 확인
```

### 문제 5: 설치 중 COM 포트 오류

```
증상: install.bat 실행 시 "8"로 저장됨
원인: batch 파일 내 PowerShell % 해석 문제
해결: install.bat에서 findstr 명령어로 COM 포트 감지

수동 설정: config.py에서 MODBUS_PORT = "COM14" 직접 수정
```

### 문제 6: 일일리포트 PDF 한글 깨짐

```
원인: FPDF에 Nanum 폰트 미등록
해결: malgun.ttf (맑은고딕) 사용
점검: C:/Windows/Fonts/malgun.ttf 존재 확인
```

---

## 부록: 파일 목록

### mecom_hmi_head (현장 HMI)

| 파일 | 설명 |
|------|------|
| `config.py` | 전역 설정 |
| `modbus_worker.py` | PLC 데이터 수집 엔진 |
| `api_server.py` | REST API 서버 |
| `app.py` | Streamlit UI |
| `head_client.py` | 본사 통신 모듈 |
| `data_provider.py` | 데이터 영속성 계층 |
| `diagram.html` | HMI 시각화 (루트, 참조용) |
| `test_plc.py` | PLC 진단 도구 |
| `sites/setup_site.py` | 현장 생성 도구 |
| `sites/default/diagram.html` | 기본 현장 HMI |
| `sites/default/background.png` | 기본 현장 배경화면 |
| `sites/template/diagram.html` | 신규 현장 템플릿 |
| `requirements.txt` | Python 의존성 |
| `start_hmi.bat` | 원클릭 실행 배치파일 |
| `install.bat` | 설치 프로그램 (Batch) |
| `install.ps1` | 설치 프로그램 (PowerShell) |
| `Dockerfile` | Docker 빌드 설정 |
| `mecomhmi_plc/mecomhmi_plc.xgwx` | LS PLC 프로젝트 파일 |
| `mecomhmi_plc/모드버스맵.xlsx` | Modbus 주소 맵 |
| `README.md` | 프로젝트 개요 |
| `CHANGELOG.md` | 변경 이력 |

### mecom_head (본사 통합관제)

| 파일 | 설명 |
|------|------|
| `config.py` | 본사 설정 |
| `api_server.py` | REST API 서버 |
| `database.py` | SQLite CRUD 계층 |
| `dashboard.py` | 관리자 대시보드 |
| `requirements.txt` | Python 의존성 |
| `AGENTS.md` | 시스템 아키텍처 문서 |
| `CHANGELOG.md` | 변경 이력 |
| `README.md` | 프로젝트 개요 |
