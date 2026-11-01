# 서재 데이터 설계

이 문서는 서재에 저장하는 논문 서지 정보의 데이터 모델, 데이터베이스 파일과 연결, 스키마 변경 방식, 논문을 저장·조회·수정·삭제하는 함수를 정한다. 무엇을 저장하는지는 [제품 비전](../ProductVision.md#3-핵심-요구사항)에, 기술 스택은 [시스템 구조](../Architecture.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 데이터 모델

모델은 [models 모듈](../../src/jjabtero/models.py)에 SQLAlchemy 선언형 매핑으로 둔다. 모든 모델은 [Base](../../src/jjabtero/models.py#Base)를 상속한다.

| 테이블 | 모델 | 내용 |
| --- | --- | --- |
| `papers` | [Paper](../../src/jjabtero/models.py#Paper) | 논문 하나의 서지 정보 |
| `authors` | [Author](../../src/jjabtero/models.py#Author) | 저자. 이름이 같으면 같은 저자로 본다. |
| `paper_authors` | [PaperAuthor](../../src/jjabtero/models.py#PaperAuthor) | 논문과 저자의 연결. 저자 순서 `position`(0부터)을 가진다. |
| `tags` | [Tag](../../src/jjabtero/models.py#Tag) | 사용자가 붙이는 태그. 이름이 같으면 같은 태그다. |
| `paper_tags` | 연결 테이블 | 논문과 태그의 다대다 연결 |

**`papers`의 열**

| 열 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `id` | 정수 | 예 | 기본 키 |
| `title` | 문자열 | 예 | 제목. 앞뒤 공백을 지우고, 비어 있으면 안 된다. |
| `item_type` | 문자열 | 예 | 항목 종류. [ITEM_TYPES](../../src/jjabtero/models.py#ITEM_TYPES) 중 하나이며 기본값은 `other`다. |
| `year` | 정수 | 아니요 | 출판 연도 |
| `venue` | 문자열 | 아니요 | 게재처(저널, 학회 이름 등) |
| `doi` | 문자열 | 아니요 | DOI. 정규화해 저장하며, 값이 있으면 서재 안에서 겹치면 안 된다. |
| `url` | 문자열 | 아니요 | 원문 주소 |
| `created_at`, `updated_at` | 시각(UTC) | 예 | 만든 시각과 마지막으로 고친 시각 |

- 항목 종류는 `journal-article`(저널 논문), `conference-paper`(학회 논문), `preprint`(프리프린트), `book`(책), `book-chapter`(책의 장), `thesis`(학위논문), `report`(보고서), `other`(그 밖)다.
- 저자와 태그는 없어도 된다. 저자는 이름 하나의 문자열로 저장하고, 성과 이름을 나누지 않는다.
- 논문을 지우면 그 논문의 저자 연결과 태그 연결도 지운다. 저자와 태그 자체는 남긴다. 다른 논문이 쓰거나 다시 쓸 수 있기 때문이다.
- [Paper.author_names](../../src/jjabtero/models.py#Paper.author_names)는 저자 이름을 순서대로, [Paper.tag_names](../../src/jjabtero/models.py#Paper.tag_names)는 태그 이름을 가나다순으로 돌려준다.
- 읽기 상태와 메모는 M1-T7에서 더한다.

## 2. 데이터베이스 파일과 연결

연결은 [db 모듈](../../src/jjabtero/db.py)이 맡는다.

- [default_db_path](../../src/jjabtero/db.py#default_db_path)는 데이터베이스 파일 경로를 돌려준다. 환경 변수 `JJABTERO_DB`가 있으면 그 경로이고, 없으면 운영체제의 사용자 데이터 폴더 아래 `Jjabtero/library.db`다(macOS: `~/Library/Application Support/Jjabtero/library.db`). 폴더는 만들지 않는다.
- 이 파일은 로컬 작업 사본이다. 구글 드라이브 `Jjabtero` 폴더와의 동기화는 M1-T9에서 이 파일을 대상으로 만든다. 저장 함수는 파일이 어디서 왔는지 모른다.
- [create_db_engine](../../src/jjabtero/db.py#create_db_engine)은 경로를 받아 SQLite 엔진을 만든다. 상위 폴더가 없으면 만든다. 연결마다 외래 키 검사(`PRAGMA foreign_keys=ON`)를 켠다. SQLite는 기본값이 꺼져 있어 연결 삭제가 동작하지 않기 때문이다.
- [upgrade_database](../../src/jjabtero/db.py#upgrade_database)는 엔진의 데이터베이스를 최신 스키마로 올린다([3. 스키마 변경](#3-스키마-변경)). 빈 파일이면 테이블을 모두 만든다.
- 백엔드 앱은 만들 때 스키마를 올리고 요청마다 세션을 연다([논문 검색과 추가 설계](PaperSearch.md#3-api)).

## 3. 스키마 변경

스키마는 Alembic 마이그레이션으로만 바꾼다. 모델을 고친 뒤 테이블을 직접 만들거나 고치지 않는다. 이미 쌓인 서재 데이터를 잃지 않고 구조를 올리기 위해서다.

- 마이그레이션 환경은 패키지 안의 `src/jjabtero/migrations/`에 둔다. 설치된 패키지에서도 `upgrade_database`가 마이그레이션을 찾게 하기 위해서다. 환경 설정은 [env 모듈](../../src/jjabtero/migrations/env.py)이다.
- 저장소 루트의 `alembic.ini`는 개발할 때 Alembic 명령(`uv run alembic revision --autogenerate -m "<설명>"`)을 쓰기 위한 설정이다. 데이터베이스 경로는 `default_db_path`와 같다.
- 마이그레이션 파일도 코드이므로 이 문서의 아래 목록에 링크하고, 파일은 이 절을 가리킨다.

| 리비전 | 내용 |
| --- | --- |
| [0001](../../src/jjabtero/migrations/versions/0001_create_library.py) | `papers`, `authors`, `paper_authors`, `tags`, `paper_tags` 테이블을 만든다. |

## 4. 저장 함수

논문 저장 함수는 [library 모듈](../../src/jjabtero/library.py)에 둔다. 모두 SQLAlchemy 세션을 첫 인자로 받고, 바꾸는 함수는 성공하면 커밋한다.

- [PaperData](../../src/jjabtero/library.py#PaperData)는 논문을 만들거나 고칠 때의 입력이다. `title`, `authors`(이름 목록, 기본 빈 목록), `item_type`(기본 `other`), `year`, `venue`, `doi`, `url`, `tags`(이름 목록, 기본 빈 목록)를 가진다. pydantic 모델이라 API 입력으로도 쓴다.
  - 제목, 저자 이름, 태그 이름은 앞뒤 공백을 지운다. 제목이 비면 검증 오류다. 빈 저자 이름과 빈 태그 이름은 버리고, 같은 태그는 한 번만 남긴다.
  - DOI는 [normalize_doi](../../src/jjabtero/library.py#normalize_doi)로 정규화한다. 앞뒤 공백과 `https://doi.org/`, `http://dx.doi.org/`, `doi:` 같은 앞부분을 지우고 소문자로 바꾼다. 결과가 `10.`으로 시작하지 않으면 검증 오류다. DOI는 대소문자를 구분하지 않으므로, 같은 논문을 두 번 넣는 것을 막는 데 쓴다.
- [add_paper](../../src/jjabtero/library.py#add_paper)는 논문을 만들어 돌려준다. 같은 이름의 저자와 태그가 있으면 그것을 쓰고, 없으면 만든다.
- [get_paper](../../src/jjabtero/library.py#get_paper)는 ID로 논문을 찾아 돌려주고, 없으면 `None`을 돌려준다.
- [list_papers](../../src/jjabtero/library.py#list_papers)는 모든 논문을 최근에 만든 것부터 돌려준다. 검색과 필터는 M1-T6에서 더한다.
- [update_paper](../../src/jjabtero/library.py#update_paper)는 논문의 모든 항목을 `PaperData`로 바꾸고 `updated_at`을 갱신한다. 저자와 태그도 입력 그대로 바꾼다.
- [delete_paper](../../src/jjabtero/library.py#delete_paper)는 논문을 지운다.

**오류**

- [PaperNotFoundError](../../src/jjabtero/library.py#PaperNotFoundError): `update_paper`, `delete_paper`에 없는 ID를 주었을 때.
- [DuplicateDoiError](../../src/jjabtero/library.py#DuplicateDoiError): 다른 논문이 이미 쓰는 DOI로 만들거나 고칠 때. 오류에 그 논문의 ID를 담는다. 데이터베이스는 바뀌지 않는다.

## 5. 테스트

테스트마다 `tmp_path`에 새 데이터베이스를 만들고 마이그레이션으로 스키마를 올린다.

- [test_db](../../tests/test_db.py)는 데이터베이스 경로의 기본값과 환경 변수, 빈 데이터베이스의 스키마 올리기와 되돌리기, 외래 키 검사를 확인한다.
- [test_library](../../tests/test_library.py)는 저장 함수 각각의 정상 동작과 오류(없는 ID, 겹치는 DOI, 빈 제목, 잘못된 DOI, 잘못된 항목 종류), 저자 순서, 태그 공유, 삭제 뒤 저자·태그가 남는지를 확인한다.
