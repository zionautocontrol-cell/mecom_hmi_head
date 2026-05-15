<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **mecom_hmi** (176 symbols, 232 relationships, 5 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/mecom_hmi/context` | Codebase overview, check index freshness |
| `gitnexus://repo/mecom_hmi/clusters` | All functional areas |
| `gitnexus://repo/mecom_hmi/processes` | All execution flows |
| `gitnexus://repo/mecom_hmi/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

<!-- ========================================================================== -->
<!-- SESSION LOG — DO NOT DELETE                                                -->
<!-- Last session: 2026-05-15                                                   -->
<!-- ========================================================================== -->

## Session Log (2026-05-15)

### Quick Start

| 사용할 연결 | 실행 명령 |
|-------------|-----------|
| RS485 (기존) | `start_hmi.bat` |
| Ethernet (신규) | `start_hmi_ethernet.bat` |

두 배치 파일 모두 같은 `modbus_worker.py`를 실행하지만, 환경변수
`MECOM_MODBUS_MODE`에 따라 `ModbusSerialClient`(RS485) 또는
`ModbusTcpClient`(Ethernet)를 생성만 달리함. 화면/알람/히스토리/본사 전송은
동일.

기존 RS485 버전은 전혀 건드리지 않았고, `start_hmi.bat`으로 그대로 사용 가능.

### What was done: v1.2 — Ethernet/TCP 연결 지원

`config.py` + `modbus_worker.py`에 RS485(Modbus RTU)와 Ethernet(Modbus TCP)을
`MECOM_MODBUS_MODE` 환경변수 하나로 전환할 수 있도록 수정함.

**핵심 변경:**

| 항목 | RS485 (rtu) | Ethernet (tcp) |
|------|-------------|----------------|
| 설정 | `MODBUS_PORT`, `MODBUS_BAUDRATE` | `MODBUS_HOST`, `MODBUS_TCP_PORT` |
| 클라이언트 | `ModbusSerialClient` | `ModbusTcpClient` |
| 실행 스크립트 | `start_hmi.bat` | `start_hmi_ethernet.bat` |

`modbus_worker.py`의 `create_modbus_client()`만 분기하고, 나머지
데이터 수집/처리/본사 전송 로직은 완전히 동일하게 재사용.

**생성된 파일:** `start_hmi_ethernet.bat`
**수정된 파일:** `config.py`, `modbus_worker.py`, `install.bat`, `CHANGELOG.md`

### Next session: possible tasks

1. `mecom_head` (본사 서버) 확인/보강
   - 현장에서 전송한 데이터가 본사 대시보드에 잘 표시되는지
   - API 인증, 알람 처리, 일일리포트 수신 확인
2. Ethernet 실제 PLC 연결 테스트
3. `start_hmi_ethernet.bat`로 실행 후 `modbus_worker.log` 연결 상태 확인
4. RS485 ↔ TCP 전환 시 `install.bat` 재실행 없이 환경변수만으로 전환 가능
