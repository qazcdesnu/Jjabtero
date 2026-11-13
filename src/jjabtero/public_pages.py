"""로그인 없이 여는 앱 소개·개인정보처리방침 페이지.

@doc: docs/design/PublicPages.md#1-제공-방식
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

ROBOTS = "noindex, nofollow"
CONTACT_URL = "https://github.com/qazcdesnu/Jjabtero/issues"
EFFECTIVE_DATE = "2026-11-14"
_USER_DATA_POLICY_URL = "https://developers.google.com/terms/api-services-user-data-policy"

# @doc: docs/design/PublicPages.md#1-제공-방식
router = APIRouter()

_STYLE = """
body { margin: 0; background: #fff; color: #1f2328; font: 16px/1.65 system-ui, sans-serif; }
main { max-width: 44rem; margin: 0 auto; padding: 2rem 1rem 4rem; }
h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
h2 { font-size: 1.15rem; margin-top: 2rem; }
hr { margin: 3rem 0; border: none; border-top: 1px solid #d0d7de; }
a { color: #0969da; }
.muted { color: #59636e; }
@media (prefers-color-scheme: dark) {
  body { background: #0d1117; color: #e6edf3; }
  hr { border-top-color: #30363d; }
  a { color: #4493f8; }
  .muted { color: #9198a1; }
}
"""


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="{ROBOTS}">
<title>{title}</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
    return HTMLResponse(html, headers={"X-Robots-Tag": ROBOTS})


_ABOUT = """
<h1>Jjabtero</h1>
<p class="muted">개인용 참고문헌 관리 앱</p>

<p>Jjabtero는 운영자 한 사람이 자기 논문 서재를 관리하려고 만든 앱입니다. 운영자 본인만 쓰며, 다른 사람의 가입이나 사용은 받지 않습니다.</p>

<h2>하는 일</h2>
<ul>
<li>OpenAlex와 arXiv에서 논문을 검색해 서재에 추가합니다.</li>
<li>서재 목록을 글자, 태그, 항목 종류, 연도로 거릅니다.</li>
<li>논문마다 읽기 상태와 메모를 남깁니다.</li>
</ul>

<h2>구글 계정을 쓰는 곳</h2>
<ul>
<li><strong>로그인</strong>: 구글 로그인으로 이메일 주소를 확인하고, 운영자 본인 계정일 때만 들여보냅니다.</li>
<li><strong>구글 드라이브 동기화</strong>: 서재 파일 하나를 운영자의 구글 드라이브에 보관합니다. 앱이 만든 파일에만 접근합니다.</li>
</ul>

<p>자세한 내용은 <a href="/privacy">개인정보처리방침</a>에 있습니다.</p>

<hr>

<h1 lang="en">Jjabtero</h1>
<p class="muted" lang="en">A personal reference manager</p>
<div lang="en">
<p>Jjabtero is a reference manager built by its operator to organize their own library of papers. Only the operator uses it; it does not accept sign-ups or other users.</p>
<h2>What it does</h2>
<ul>
<li>Searches papers on OpenAlex and arXiv and adds them to the library.</li>
<li>Filters the library by text, tag, item type and year.</li>
<li>Keeps a reading status and notes for each paper.</li>
</ul>
<h2>How it uses a Google account</h2>
<ul>
<li><strong>Sign-in</strong>: Google Sign-In checks the email address and admits only the operator's own account.</li>
<li><strong>Google Drive sync</strong>: stores one library file in the operator's Google Drive. The app only accesses files it created.</li>
</ul>
<p>See the <a href="/privacy">privacy policy</a> for details.</p>
</div>
"""

_PRIVACY = f"""
<h1>개인정보처리방침</h1>
<p class="muted">시행일: {EFFECTIVE_DATE}</p>

<p>이 방침은 Jjabtero(<a href="/about">앱 소개</a>)가 구글 사용자 데이터를 어떻게 받고, 쓰고, 보관하는지 설명합니다. Jjabtero는 운영자 본인만 쓰는 앱입니다.</p>

<h2>받는 데이터와 쓰는 곳</h2>
<ul>
<li><strong>로그인(<code>openid email</code>)</strong>: 구글 계정의 이메일 주소를 받습니다. 허용한 계정인지 확인하는 데만 쓰며, 서명된 세션 쿠키에만 담습니다. 이름, 사진 등 다른 정보는 받지 않습니다.</li>
<li><strong>구글 드라이브(<code>drive.file</code>)</strong>: 앱이 만든 파일만 읽고 씁니다. 서재를 드라이브의 <code>Jjabtero/library.db</code> 파일 하나에 보관합니다. 드라이브의 다른 파일에는 접근하지 않습니다.</li>
</ul>

<h2>보관</h2>
<ul>
<li>드라이브 갱신 토큰은 서버의 비밀 설정에 보관합니다.</li>
<li>서재의 작업 사본은 서버 디스크에 두며, 서버가 다시 시작될 때 지워집니다. 서재의 원본은 운영자의 구글 드라이브에 있습니다.</li>
</ul>

<h2>공유하지 않음</h2>
<ul>
<li>구글 사용자 데이터를 팔거나 다른 사람에게 넘기지 않습니다.</li>
<li>광고, 분석, AI 모델 학습에 쓰지 않습니다.</li>
<li>논문을 검색할 때 검색어를 OpenAlex와 arXiv에 보내지만, 구글 사용자 데이터는 보내지 않습니다.</li>
</ul>

<p>Jjabtero가 구글 API에서 받은 정보를 쓰고 다른 앱으로 옮기는 일은 제한적 사용(Limited Use) 요건을 포함한 <a href="{_USER_DATA_POLICY_URL}">Google API 서비스 사용자 데이터 정책</a>을 따릅니다.</p>

<h2>삭제</h2>
<ul>
<li>구글 계정의 <a href="https://myaccount.google.com/connections">서드 파티 앱 및 서비스</a>에서 Jjabtero의 접근 권한을 언제든 취소할 수 있습니다.</li>
<li>구글 드라이브의 <code>Jjabtero</code> 폴더를 지우면 서재가 지워집니다.</li>
</ul>

<h2>연락처</h2>
<p><a href="{CONTACT_URL}">GitHub 저장소의 이슈</a>로 문의해 주세요.</p>

<hr>

<div lang="en">
<h1>Privacy Policy</h1>
<p class="muted">Effective date: {EFFECTIVE_DATE}</p>
<p>This policy explains how Jjabtero (<a href="/about">about</a>) receives, uses and stores Google user data. Jjabtero is used only by its operator.</p>
<h2>Data received and how it is used</h2>
<ul>
<li><strong>Sign-in (<code>openid email</code>)</strong>: the Google account's email address. It is used only to check that the account is the allowed one and is kept only in a signed session cookie. No name, photo or other profile data is received.</li>
<li><strong>Google Drive (<code>drive.file</code>)</strong>: the app reads and writes only files it created. The library is stored in a single file, <code>Jjabtero/library.db</code>, in Drive. No other Drive files are accessed.</li>
</ul>
<h2>Storage</h2>
<ul>
<li>The Drive refresh token is kept in the server's secret configuration.</li>
<li>A working copy of the library lives on the server disk and is erased when the server restarts. The original is in the operator's Google Drive.</li>
</ul>
<h2>No sharing</h2>
<ul>
<li>Google user data is not sold or transferred to anyone.</li>
<li>It is not used for advertising, analytics or training AI models.</li>
<li>Paper search queries are sent to OpenAlex and arXiv, but no Google user data is sent to them.</li>
</ul>
<p>Jjabtero's use and transfer to any other app of information received from Google APIs will adhere to the <a href="{_USER_DATA_POLICY_URL}">Google API Services User Data Policy</a>, including the Limited Use requirements.</p>
<h2>Deletion</h2>
<ul>
<li>Access can be revoked at any time under <a href="https://myaccount.google.com/connections">Third-party apps &amp; services</a> in the Google Account.</li>
<li>Deleting the <code>Jjabtero</code> folder in Google Drive deletes the library.</li>
</ul>
<h2>Contact</h2>
<p>Please open an issue on the <a href="{CONTACT_URL}">GitHub repository</a>.</p>
</div>
"""


@router.get("/about", response_class=HTMLResponse)
def about() -> HTMLResponse:
    """앱 소개 페이지.

    @doc: docs/design/PublicPages.md#3-내용
    """
    return _page("Jjabtero 소개", _ABOUT)


@router.get("/privacy", response_class=HTMLResponse)
def privacy() -> HTMLResponse:
    """개인정보처리방침 페이지.

    @doc: docs/design/PublicPages.md#3-내용
    """
    return _page("Jjabtero 개인정보처리방침", _PRIVACY)
