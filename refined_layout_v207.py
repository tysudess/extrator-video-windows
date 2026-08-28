import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import refined_layout_v206 as v206

try:
    import websocket
except Exception:
    websocket = None

APP_VERSION = 'Windows Portable v2.0.7 — R7 Browser HLS Capture + HLS/TS + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.7  •  R7 BROWSER HLS'

core = v206.core
v205 = v206.v205
v203 = v206.v203


def _browser_candidates():
    candidates = []
    env_paths = (
        os.environ.get('PROGRAMFILES(X86)', ''),
        os.environ.get('PROGRAMFILES', ''),
        os.environ.get('LOCALAPPDATA', ''),
    )
    for root in env_paths:
        if not root:
            continue
        candidates.extend([
            Path(root) / 'Microsoft/Edge/Application/msedge.exe',
            Path(root) / 'Google/Chrome/Application/chrome.exe',
        ])
    seen = set()
    result = []
    for item in candidates:
        key = str(item).lower()
        if key not in seen and item.exists():
            seen.add(key)
            result.append(item)
    return result


def _free_local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _proxy_for_browser(proxy_url):
    value = str(proxy_url or '').strip()
    if not value:
        return ''
    try:
        parsed = urllib.parse.urlparse(value if '://' in value else 'http://' + value)
        if not parsed.hostname:
            return ''
        host = parsed.hostname
        port = f':{parsed.port}' if parsed.port else ''
        scheme = parsed.scheme if parsed.scheme in ('http', 'https', 'socks4', 'socks5') else 'http'
        return f'{scheme}://{host}{port}'
    except Exception:
        return ''


def _is_manifest_url(url, mime=''):
    low = str(url or '').lower()
    mime_low = str(mime or '').lower()
    return '.m3u8' in low or 'mpegurl' in mime_low or 'vnd.apple' in mime_low


def _rank_manifests(urls):
    unique = []
    seen = set()
    for raw in urls:
        url = str(raw or '').strip()
        if not re.match(r'(?i)^https?://', url) or url in seen:
            continue
        seen.add(url)
        unique.append(url)

    def score(url):
        low = urllib.parse.unquote(url.lower())
        points = 0
        if 'master' in low:
            points += 50
        if 'manifest' in low:
            points += 35
        if 'playlist' in low:
            points += 25
        if 'index' in low:
            points += 10
        if 'chunklist' in low or 'media_' in low:
            points -= 25
        if re.search(r'(?<!\d)(2160|1440|1080|720|540|480|360|240)p?(?!\d)', low):
            points -= 12
        return points

    return sorted(unique, key=score, reverse=True)


def _send_cdp(ws, message_id, method, params=None, session_id=''):
    payload = {'id': int(message_id), 'method': method}
    if params is not None:
        payload['params'] = params
    if session_id:
        payload['sessionId'] = session_id
    ws.send(json.dumps(payload))


def _capture_r7_hls_browser(page_url, proxy_url='', timeout_seconds=16):
    """Abre Edge/Chrome headless e observa os manifests HLS realmente requisitados.

    O extrator nativo antigo do R7 usa player-api/player.r7.com, endpoints que hoje
    podem responder 404. Esta captura observa a mesma navegação que um gerenciador
    de downloads vê e devolve apenas URLs HLS reais; nenhum ID interno é enviado ao
    yt-dlp como se fosse uma URL de mídia.
    """
    if websocket is None:
        return []
    browsers = _browser_candidates()
    if not browsers:
        return []

    browser = browsers[0]
    port = _free_local_port()
    profile_dir = tempfile.mkdtemp(prefix='extrator-r7-edge-')
    process = None
    ws = None
    manifests = []

    args = [
        str(browser),
        '--headless=new',
        '--disable-gpu',
        '--disable-extensions',
        '--disable-background-networking',
        '--no-first-run',
        '--no-default-browser-check',
        '--autoplay-policy=no-user-gesture-required',
        '--remote-allow-origins=*',
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
        '--window-size=1365,900',
    ]
    browser_proxy = _proxy_for_browser(proxy_url)
    if browser_proxy:
        args.append(f'--proxy-server={browser_proxy}')
    args.append('about:blank')

    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )

        targets = None
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=1) as response:
                    targets = json.loads(response.read().decode('utf-8', 'replace'))
                if targets:
                    break
            except Exception:
                time.sleep(0.2)
        if not targets:
            return []

        target = next((item for item in targets if item.get('type') == 'page'), targets[0])
        ws_url = target.get('webSocketDebuggerUrl')
        if not ws_url:
            return []

        ws = websocket.create_connection(
            ws_url,
            timeout=1.0,
            origin='http://127.0.0.1',
            http_proxy_host=None,
        )
        msg_id = 1
        _send_cdp(ws, msg_id, 'Network.enable'); msg_id += 1
        _send_cdp(ws, msg_id, 'Page.enable'); msg_id += 1
        _send_cdp(ws, msg_id, 'Runtime.enable'); msg_id += 1
        _send_cdp(ws, msg_id, 'Target.setAutoAttach', {
            'autoAttach': True,
            'waitForDebuggerOnStart': False,
            'flatten': True,
        }); msg_id += 1
        _send_cdp(ws, msg_id, 'Page.navigate', {'url': page_url}); msg_id += 1

        start = time.time()
        last_nudge = 0.0
        while time.time() - start < timeout_seconds:
            elapsed = time.time() - start
            if elapsed - last_nudge > 2.5:
                script = """
                    (() => {
                      const el = document.querySelector('video, iframe[src*="player"], iframe[src*="video"], [id^="player-"], .embed');
                      if (el) el.scrollIntoView({block:'center'});
                      document.querySelectorAll('video').forEach(v => { try { v.muted = true; v.play(); } catch(e) {} });
                    })();
                """
                try:
                    _send_cdp(ws, msg_id, 'Runtime.evaluate', {'expression': script}); msg_id += 1
                except Exception:
                    pass
                last_nudge = elapsed

            try:
                raw = ws.recv()
            except Exception:
                continue
            try:
                event = json.loads(raw)
            except Exception:
                continue

            method = event.get('method', '')
            params = event.get('params') or {}
            if method == 'Target.attachedToTarget':
                session = params.get('sessionId') or ''
                if session:
                    try:
                        _send_cdp(ws, msg_id, 'Network.enable', session_id=session); msg_id += 1
                        _send_cdp(ws, msg_id, 'Runtime.enable', session_id=session); msg_id += 1
                    except Exception:
                        pass
                continue

            if method == 'Network.requestWillBeSent':
                url = ((params.get('request') or {}).get('url') or '')
                if _is_manifest_url(url):
                    manifests.append(url)
            elif method == 'Network.responseReceived':
                response = params.get('response') or {}
                url = response.get('url') or ''
                if _is_manifest_url(url, response.get('mimeType') or ''):
                    manifests.append(url)

            ranked = _rank_manifests(manifests)
            # Um master/manifest real já basta; esperamos um pouco para capturar
            # variantes adicionais, sem ficar presos no navegador.
            if ranked and elapsed > 6.0:
                break

        return _rank_manifests(manifests)[:12]
    except Exception:
        return []
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        shutil.rmtree(profile_dir, ignore_errors=True)


def _article_scoped_static_streams(page_url, proxy_url=''):
    """Fallback estático: restringe HLS/MP4 ao bloco do player principal."""
    try:
        page_html = core.fetch_html(page_url, proxy_url)
    except Exception:
        return []

    text = str(page_html or '')
    ids = []

    h1_pos = text.lower().find('<h1')
    related_match = re.search(r'(?is)(?:veja\s+tamb[eé]m|ultimas|últimas)', text[max(0, h1_pos):] if h1_pos >= 0 else text)
    if h1_pos >= 0:
        related_pos = (h1_pos + related_match.start()) if related_match else min(len(text), h1_pos + 500000)
        article_slice = text[max(0, h1_pos - 30000):related_pos]
        ids = v203._r7_video_ids(article_slice)
    if not ids:
        ids = v203._r7_video_ids(text)

    result = []
    seen = set()

    def add_many(values):
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)

    # Procura mídia no contexto do primeiro player da matéria, em vez de varrer
    # primeiro todos os vídeos relacionados da página.
    for video_id in ids[:2]:
        pos = text.lower().find(video_id.lower())
        if pos < 0:
            continue
        local = text[max(0, pos - 140000):min(len(text), pos + 140000)]
        add_many(v205._extract_stream_urls(local, page_url))
        if result:
            break

    if not result and h1_pos >= 0:
        end = min(len(text), related_pos if 'related_pos' in locals() else h1_pos + 500000)
        add_many(v205._extract_stream_urls(text[max(0, h1_pos - 50000):end], page_url))

    return _rank_manifests(result) + [u for u in result if u not in _rank_manifests(result)]


def _resolve_r7_candidates_v207(page_url, proxy_url=''):
    page_url = v205._clean_r7_url(page_url)

    # 1) Fonte principal: tráfego real do player no navegador, equivalente ao
    # que o IDM observa quando o R7 começa a reproduzir o vídeo.
    captured = _capture_r7_hls_browser(page_url, proxy_url)
    if captured:
        return captured[:12]

    # 2) Contingência: HTML estático restrito ao player principal.
    static = _article_scoped_static_streams(page_url, proxy_url)
    media_only = [
        url for url in static
        if any(ext in url.lower() for ext in ('.m3u8', '.mp4', '.m4v'))
    ]
    return media_only[:20]


# Substitui o resolver usado dinamicamente pelos workers R7 já existentes.
# Importante: esta versão NUNCA devolve player.r7.com/video/i/<id> ao yt-dlp.
v203._resolve_r7_candidates = _resolve_r7_candidates_v207

core.APP_VERSION = APP_VERSION
v203.APP_VERSION = APP_VERSION
v203.SIDEBAR_VERSION = SIDEBAR_VERSION
v205.APP_VERSION = APP_VERSION
v205.SIDEBAR_VERSION = SIDEBAR_VERSION
v206.APP_VERSION = APP_VERSION
v206.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v203.APP_VERSION = APP_VERSION
    v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    v205.APP_VERSION = APP_VERSION
    v205.SIDEBAR_VERSION = SIDEBAR_VERSION
    v206.APP_VERSION = APP_VERSION
    v206.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v206.main()


if __name__ == '__main__':
    main()
