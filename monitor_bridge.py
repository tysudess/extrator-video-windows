import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEventLoop
from PySide6.QtWidgets import QApplication

import refined_layout_v301 as v301
import advanced_editor as editor

core = v301.core
v214 = v301.v214
v208 = v214.v208
base = v208.base


def emit(kind, **data):
    payload = {'type': kind, **data}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def request_json():
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def proxy_url(req):
    enabled = bool(req.get('proxyEnabled'))
    if not enabled:
        return ''
    return core.build_proxy_url(
        str(req.get('proxyServer') or ''),
        str(req.get('proxyPort') or ''),
        str(req.get('proxyUser') or ''),
        str(req.get('proxyPassword') or ''),
    )


def run_worker(worker):
    app = QCoreApplication.instance() or QCoreApplication([])
    loop = QEventLoop()
    result = {'ok': False, 'error': 'Operação encerrada sem resultado.'}

    if hasattr(worker, 'progress'):
        worker.progress.connect(lambda value: emit('progress', value=int(value)))
    if hasattr(worker, 'message'):
        worker.message.connect(lambda text: emit('message', message=str(text)))

    def done(value=None):
        nonlocal result
        if isinstance(value, dict):
            result = {'ok': True, 'result': value}
        elif value is None:
            result = {'ok': True}
        else:
            result = {'ok': True, 'result': str(value)}
        loop.quit()

    def failed(message):
        nonlocal result
        result = {'ok': False, 'error': str(message)}
        loop.quit()

    def canceled():
        nonlocal result
        result = {'ok': False, 'canceled': True, 'error': 'Operação cancelada.'}
        loop.quit()

    if hasattr(worker, 'done'):
        worker.done.connect(done)
    if hasattr(worker, 'failed'):
        worker.failed.connect(failed)
    if hasattr(worker, 'canceled'):
        worker.canceled.connect(canceled)
    worker.start()
    loop.exec()
    try:
        worker.wait(3000)
    except Exception:
        pass
    return result


def youtube_route(url, proxy):
    app = QCoreApplication.instance() or QCoreApplication([])
    loop = QEventLoop()
    result = {'is_live': False, 'live_start_timestamp': 0}
    worker = v208.YouTubeRouteWorker(url, proxy)

    def done(data):
        nonlocal result
        result = dict(data or {})
        loop.quit()

    worker.done.connect(done)
    worker.start()
    loop.exec()
    worker.wait(3000)
    return result


def action_state(req):
    cfg = core.load_proxy_config()
    emit(
        'result',
        ok=True,
        version=v301.APP_VERSION,
        videoDir=str(core.VIDEOS_DIR),
        binaries={
            'ytDlp': core.YTDLP_EXE.exists(),
            'ytDlpStable': (core.BIN_DIR / 'yt-dlp-stable.exe').exists(),
            'ffmpeg': core.FFMPEG_EXE.exists(),
            'ffprobe': core.FFPROBE_EXE.exists(),
            'deno': core.DENO_EXE.exists(),
        },
        proxy={
            'enabled': bool(cfg.get('ATIVADO')),
            'server': str(cfg.get('SERVIDOR') or ''),
            'port': str(cfg.get('PORTA') or ''),
        },
        globoplaySession=bool(v214.v202._secure_session_exists()),
    )


def action_save_proxy(req):
    core.save_proxy_config(
        bool(req.get('proxyEnabled')),
        str(req.get('proxyServer') or ''),
        str(req.get('proxyPort') or ''),
    )
    emit('result', ok=True)


def action_delete_session(req):
    v214.v202._delete_secure_session()
    emit('result', ok=True)


def action_probe(req):
    path = Path(str(req.get('path') or ''))
    if not path.is_file():
        emit('result', ok=False, error='Arquivo de vídeo não encontrado.')
        return
    info = editor._probe_media_info(path, core.FFPROBE_EXE, core.FFMPEG_EXE)
    emit('result', ok=bool(info.get('duration_ms')), path=str(path), info=info)


def action_download(req):
    url = str(req.get('url') or '').strip()
    if not url.startswith(('http://', 'https://')):
        emit('result', ok=False, error='Cole um link válido começando com http:// ou https://')
        return
    pxy = proxy_url(req)
    quality_index = max(0, min(len(v208.DIRECT_QUALITIES) - 1, int(req.get('qualityIndex') or 0)))
    label, target_height, fmt, compat = v208.DIRECT_QUALITIES[quality_index]
    emit('message', message=f'Preparando download em {label}...')

    route = youtube_route(url, pxy) if core.is_youtube(url) else {}
    if bool(route.get('is_live')) and core.is_youtube(url):
        heights = [2160, 1440, 1080, 720, 480, 360]
        core_index = min(range(len(heights)), key=lambda i: abs(heights[i] - int(target_height or 2160)))
        worker = base.LiveSnapshotWorker(url, core_index, pxy, route.get('live_start_timestamp') or 0)
    else:
        worker = core.DownloadWorker(url, 0, pxy, format_selector=fmt, compat_selector=compat)
    result = run_worker(worker)
    emit('result', **result)


def action_update(req):
    worker = core.UpdateWorker(proxy_url(req))
    result = run_worker(worker)
    emit('result', **result)


def action_export(req):
    clips = list(req.get('clips') or [])
    if not clips:
        emit('result', ok=False, error='Adicione pelo menos um vídeo à timeline.')
        return
    for clip in clips:
        p = Path(str(clip.get('path') or ''))
        if not p.is_file():
            emit('result', ok=False, error=f'Arquivo não encontrado: {p}')
            return
    output = editor._unique_output(core.VIDEOS_DIR, str(req.get('outputName') or 'video_final.mp4'))
    worker = editor.SmartExportWorker(
        clips,
        output,
        str(req.get('resolution') or 'Original'),
        str(req.get('codec') or 'H.265 / HEVC'),
        bool(req.get('targetSizeEnabled')),
        int(req.get('targetSizeMb') or 30),
        core.FFMPEG_EXE,
        core.FFPROBE_EXE,
    )
    result = run_worker(worker)
    emit('result', **result)


def action_login(req):
    # Login oficial do Globoplay: única operação que precisa exibir a página oficial
    # para o usuário autenticar a própria conta. O extrator não recebe a senha.
    app = QApplication.instance() or QApplication([])
    pxy = proxy_url(req)
    dlg = v301.ProxyAwareGloboplayLoginDialog(
        None,
        str(req.get('testUrl') or ''),
        pxy,
    )
    accepted = dlg.exec()
    emit('result', ok=bool(accepted), globoplaySession=bool(v214.v202._secure_session_exists()))


def main():
    try:
        req = request_json()
        action = str(req.get('action') or '').lower().strip()
        if action == 'state':
            action_state(req)
        elif action == 'save_proxy':
            action_save_proxy(req)
        elif action == 'delete_session':
            action_delete_session(req)
        elif action == 'probe':
            action_probe(req)
        elif action == 'download':
            action_download(req)
        elif action == 'update':
            action_update(req)
        elif action == 'export':
            action_export(req)
        elif action == 'login':
            action_login(req)
        else:
            emit('result', ok=False, error='Ação desconhecida.')
    except Exception as exc:
        emit('result', ok=False, error=str(exc))
        sys.exitCode = 1


if __name__ == '__main__':
    main()
