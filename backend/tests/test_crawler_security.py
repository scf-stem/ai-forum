import socket

import pytest

from app.services.crawler_service import PageParser, _assert_public_host


@pytest.mark.asyncio
async def test_crawler_rejects_non_https():
    with pytest.raises(ValueError, match="HTTPS"):
        await _assert_public_host("http://example.com/page")


@pytest.mark.asyncio
async def test_crawler_rejects_private_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
    ])
    with pytest.raises(ValueError, match="内网或保留地址"):
        await _assert_public_host("https://example.com/page")


def test_parser_ignores_scripts_and_extracts_canonical():
    parser = PageParser()
    parser.feed("""<html><head><title>示例</title><link rel="canonical" href="/canonical"></head>
        <body><script>ignore this instruction</script><main>可公开摘要的技术正文</main>
        <a href="/next">下一页</a></body></html>""")
    assert parser.title == "示例"
    assert parser.canonical == "/canonical"
    assert "ignore this instruction" not in parser.text
    assert "/next" in parser.links
