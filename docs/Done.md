# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## I3 ProjInit 0.1.2 업그레이드

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [검증 도구의 설정](VerificationTools.md#11-설정)

### 계획
- `projinit.toml`의 `version`을 0.1.2로 바꾼다.
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.2 projinit init --refresh-common`으로 공통 파일을 다시 만든다.
- 바뀐 규칙을 확인해 사용자에게 알리고, 프로젝트 문서가 바뀐 규칙에 맞는지 검사를 통과시킨다.

### 진행 기록
- 2026-10-31: 사용자 지시로 이슈를 등록하고 시작했다. PR #1이 병합되지 않아 `i1-remote-repository` 위에 작업 브랜치를 만들었다.
- 2026-10-31: `version`을 0.1.2로 바꾸고 `init --refresh-common`을 실행했다. 공통 파일 6개가 다시 쓰였다. 규칙 변경은 `docs/TaskRule.md`에 4.9 ProjInit 버전 올리기 절이 추가된 것뿐이고, 나머지 파일은 검사기 명령의 버전만 바뀌었다. 진행 중인 다른 작업이 없어 영향받는 작업은 없다.

### 결정 사항
- 규칙 문서와 검사기 버전이 바뀌므로 경량 이슈가 아닌 일반 경로로 처리한다.

### 변경 파일
- `projinit.toml`
- `.claude/settings.json`
- `.githooks/commit-msg`
- `.githooks/pre-commit`
- `.github/pull_request_template.md`
- `.github/workflows/verify.yml`
- `docs/TaskRule.md`
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 프로젝트가 ProjInit 0.1.2 검사기와 공통 규칙 문서를 쓴다. ProjInit 버전을 올리는 절차가 [작업 관리 규칙](TaskRule.md#49-projinit-버전-올리기)에 생겼다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.2 projinit check`: 모든 검사기 통과(check_docs, check_pointers, check_tasks, check_hooks, check_commits, check_template).

## I2 ProjInit 0.1.1 업그레이드

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [검증 도구의 설정](VerificationTools.md#11-설정)

### 계획
- 작업 트리에 생긴 ProjInit 0.1.1 업그레이드 변경을 확인하고, I1과 섞지 않고 별도 커밋으로 반영한다.

### 진행 기록
- 2026-10-31: I1 작업 중 작업 트리에서 ProjInit 버전이 0.1.0에서 0.1.1로 바뀐 것을 발견했다. `projinit.toml`의 `version`, `.claude/settings.json`, `.githooks/pre-commit`, `.githooks/commit-msg`, `.github/` 파일의 검사기 명령, `docs/TaskRule.md`의 4.8 첫 작업 절차가 바뀌어 있었다.
- 2026-10-31: 사용자가 의도한 업그레이드임을 확인했고, I2로 등록해 I1과 같은 PR의 별도 커밋으로 처리하기로 했다.

### 결정 사항
- 업그레이드는 규칙 문서(`docs/TaskRule.md`)와 검사기 버전을 바꾸므로 경량 이슈가 아닌 일반 경로로 처리한다.
- I1과 같은 작업 브랜치 `i1-remote-repository`에서 처리하되 커밋은 나눈다([커밋 규칙](CommitRule.md#2-커밋-단위와-시점)).

### 변경 파일
- `projinit.toml`(`version`만)
- `.claude/commands/start.md`
- `.claude/settings.json`
- `.githooks/commit-msg`
- `.githooks/pre-commit`
- `.github/pull_request_template.md`
- `.github/workflows/verify.yml`
- `docs/TaskRule.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 프로젝트가 ProjInit 0.1.1 검사기와 공통 규칙 문서를 쓴다. 첫 작업 절차가 질문을 하나씩 가볍게 하는 방식으로 바뀌었다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.1 projinit check`: 모든 검사기 통과(check_docs, check_pointers, check_tasks, check_hooks, check_commits, check_template).
