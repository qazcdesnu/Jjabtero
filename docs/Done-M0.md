# 완료 보관 M0 시작

이 문서는 닫힌 마일스톤 M0 시작의 완료 기록을 보관한다. 기록 형식과 순서는 [완료](Done.md)와 같으며, 진행 중인 마일스톤의 기록은 완료 문서에 있다.

## M0-T1 제품 비전과 첫 로드맵 작성

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [작업 관리 규칙의 첫 작업](TaskRule.md#48-첫-작업)

### 계획
- 사용자와 대화로 목적과 쓰는 사람, 꼭 필요한 기능, 개발 언어와 기술 스택, 원격 저장소를 정한다. 정하지 않은 것은 미결정 사항으로 남긴다.
- 제품 비전(`docs/ProductVision.md`)과 시스템 구조(`docs/Architecture.md`)를 쓰고 문서 인덱스에서 링크한다. 루트 `README.md`를 쓴다.
- `projinit.toml`의 `check.commands`와 `template.repository`를 채우고 공통 문서를 다시 만든다.
- 로드맵에 첫 마일스톤과 태스크를 적는다.
- 검증을 통과시키고 완료 처리한 뒤 첫 커밋을 한다.

### 진행 기록
- 2026-10-31: `/start`로 작업을 시작했다. 아직 `main`이 없어 작업 브랜치는 만들지 않았다.
- 2026-10-31: 사용자와 대화로 방향을 정했다. 목적은 데이터사이언스 대학원생 본인을 위한 개인 서지관리 앱이고, Zotero를 대체한다. 사용자는 본인 한 명이다. 언어는 Python, 테스트는 pytest, 형태는 로컬 웹 앱이다. 원격 저장소는 아직 없고 나중에 만든다.
- 2026-10-31: 사용자가 고른 기능은 논문 검색·필터, 읽기 상태·메모 관리, 서재 통계·시각화, 인용 거리 기반 연결·추천(임베딩 기반 대신)이다. 사용자는 세부 사항을 만들면서 정하기를 원했다.
- 2026-10-31: 제품 비전, 시스템 구조, README를 쓰고 인덱스에서 링크했다. 로드맵에 M1 기본 서재를 적었다.
- 2026-10-31: `projinit init --refresh-common`을 실행했다. 설정 값이 바뀌지 않아 다시 쓴 공통 문서는 0개다.

### 결정 사항
- 사용자가 정하지 않은 웹 프레임워크, 데이터 저장 방식, 논문 추가 방법, 인용 데이터 출처 등은 [제품 비전](ProductVision.md#5-미결정-사항)과 [시스템 구조](Architecture.md#6-미결정-사항)의 미결정 사항으로 남겼다.
- `check.commands`에 `uv run pytest`를 아직 등록하지 않는다. `pyproject.toml`과 테스트가 없으면 pytest가 실패하기 때문이다. 골격을 만드는 M1-T1에서 등록한다.
- `template.repository`는 원격 저장소가 아직 없으므로 "아직 없음"으로 둔다.
- M1은 서재의 기본 기능과 검색·필터, 읽기 상태·메모로 정했다. 인용 기반 연결·추천과 통계·시각화는 서재 데이터가 있어야 만들 수 있으므로 다음 마일스톤으로 미룬다.

### 변경 파일
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `README.md`
- `docs/index.md`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/Done-M0.md`

### 결과
- 제품 비전과 시스템 구조가 생겨 무엇을 어떤 구조로 만드는지 문서로 확인할 수 있다. 정하지 않은 항목은 미결정 사항으로 남겼다.
- 로드맵에 첫 마일스톤 M1 기본 서재가 있어 다음 작업을 시작할 수 있다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.0 projinit check`: 모든 검사기 통과(check_docs, check_pointers, check_tasks, check_hooks, check_commits, check_template). 등록된 프로젝트 명령은 아직 없다.
