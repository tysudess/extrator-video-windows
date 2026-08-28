import html
import re
import unicodedata
import urllib.parse

import refined_layout_v205 as v205

APP_VERSION = 'Windows Portable v2.0.6 — R7 Primary Player Fix + HLS/TS + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.6  •  R7 PRIMARY PLAYER FIX'

core = v205.core
v203 = v205.v203
v204 = v205.v204


_STOPWORDS = {
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'na', 'no',
    'nas', 'nos', 'para', 'por', 'com', 'um', 'uma', 'uns', 'umas', 'ao', 'aos',
    'esta', 'este', 'essa', 'esse', 'desta', 'deste', 'dessa', 'desse', 'que',
    'r7', 'record', 'noticias', 'video', 'videos', 'conteudo', 'exclusivo'
}


def _plain_text(value):
    text = html.unescape(str(value or ''))
    text = re.sub(r'(?is)<script\b.*?</script>', ' ', text)
    text = re.sub(r'(?is)<style\b.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _normalize_text(value):
    text = _plain_text(value).lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _tokens(value):
    return {
        token for token in _normalize_text(value).split()
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _article_title(page_html, page_url):
    text = str(page_html or '')
    patterns = (
        r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'(?is)<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r'(?is)<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)',
        r'(?is)<h1[^>]*>(.*?)</h1>',
        r'(?is)<title[^>]*>(.*?)</title>',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            title = _plain_text(match.group(1))
            title = re.sub(r'\s*[|\-–—]\s*(?:Noticias R7|Notícias R7|R7|Record(?: TV)?)\s*$', '', title, flags=re.I)
            if len(title) >= 8:
                return title.strip()
    try:
        slug = urllib.parse.urlparse(page_url).path.rstrip('/').split('/')[-1]
        slug = re.sub(r'-\d{8}$', '', slug)
        return slug.replace('-', ' ').strip()
    except Exception:
        return ''


def _payload_labels(value):
    labels = []
    interesting = {
        'title', 'titulo', 'name', 'headline', 'description', 'descricao', 'slug',
        'video_title', 'videoTitle', 'media_title', 'mediaTitle'
    }

    def walk(obj):
        if isinstance(obj, dict):
            for key, item in obj.items():
                if isinstance(item, str) and key in interesting:
                    clean = _plain_text(item)
                    if 5 <= len(clean) <= 500:
                        labels.append(clean)
                elif isinstance(item, (dict, list, tuple)):
                    walk(item)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)

    walk(value)
    return labels


def _text_similarity(reference, candidate):
    ref = _tokens(reference)
    cand = _tokens(candidate)
    if not ref or not cand:
        return 0.0
    common = ref & cand
    # Favorece cobertura do título da matéria e penaliza metadados genéricos.
    coverage = len(common) / max(1, len(ref))
    precision = len(common) / max(1, len(cand))
    score = (coverage * 0.78) + (precision * 0.22)
    nr = _normalize_text(reference)
    nc = _normalize_text(candidate)
    if nr and nc and (nr in nc or nc in nr):
        score += 0.45
    return score


def _context_for_id(page_html, video_id, radius=3500):
    text = str(page_html or '')
    position = text.lower().find(str(video_id).lower())
    if position < 0:
        return ''
    start = max(0, position - radius)
    end = min(len(text), position + len(video_id) + radius)
    return _plain_text(text[start:end])


def _player_payload(video_id, page_url, proxy_url=''):
    for api_url in (
        f'https://player-api.r7.com/video/i/{video_id}',
        f'http://player-api.r7.com/video/i/{video_id}',
    ):
        try:
            payload = v203._request_json(api_url, proxy_url, page_url)
            if isinstance(payload, (dict, list)):
                return payload
        except Exception:
            pass
    return None


def _rank_primary_players(page_html, page_url, proxy_url=''):
    article = _article_title(page_html, page_url)
    ranked = []
    for order, video_id in enumerate(v203._r7_video_ids(page_html)):
        payload = _player_payload(video_id, page_url, proxy_url)
        label_score = 0.0
        if payload is not None:
            for label in _payload_labels(payload):
                label_score = max(label_score, _text_similarity(article, label))
        context_score = _text_similarity(article, _context_for_id(page_html, video_id))
        # Metadados da API têm peso maior que o contexto HTML.
        score = (label_score * 2.0) + (context_score * 0.45)
        ranked.append((score, -order, video_id, payload, label_score, context_score))
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    return article, ranked


def _resolve_r7_candidates_v206(page_url, proxy_url=''):
    """Resolve somente o player principal da matéria R7.

    O HTML do R7 contém vídeos relacionados, playlists e cards de outras matérias.
    As versões anteriores podiam capturar o primeiro HLS global da página e baixar
    um vídeo diferente. Agora escolhemos primeiro o ID do player mais compatível
    com o título da matéria e só então extraímos HLS/MP4 daquele player.
    """
    page_url = v205._clean_r7_url(page_url)
    page_html = core.fetch_html(page_url, proxy_url)
    _article, ranked = _rank_primary_players(page_html, page_url, proxy_url)

    result = []
    seen = set()

    def add(url):
        final = v203._unescape_url(url)
        if final.startswith('//'):
            final = 'https:' + final
        if final and re.match(r'(?i)^https?://', final) and final not in seen:
            seen.add(final)
            result.append(final)

    if ranked:
        _score, _order, video_id, payload, _label_score, _context_score = ranked[0]

        # Primeiro: mídias declaradas pela API do player escolhido.
        if payload is not None:
            for media in v203._media_urls_from_object(payload):
                add(media)

        # Segundo: lê apenas endpoints pertencentes ao mesmo ID de player.
        endpoints = (
            f'https://player-api.r7.com/video/i/{video_id}',
            f'https://player.r7.com/video/i/{video_id}',
        )
        for endpoint in endpoints:
            try:
                raw = v205._request_text(endpoint, proxy_url, page_url)
                for media in v205._extract_stream_urls(raw, endpoint):
                    add(media)
            except Exception:
                pass

        # Último fallback ainda preso ao mesmo ID, nunca a outro vídeo relacionado.
        add(f'https://player.r7.com/video/i/{video_id}')
        return result[:20]

    # Páginas antigas sem ID interno: só então recorremos aos HLS/MP4 globais.
    for media in v205._extract_stream_urls(page_html, page_url):
        add(media)
    try:
        for candidate in core.extract_candidates_from_html(page_html, page_url):
            low = candidate.lower()
            if any(ext in low for ext in ('.m3u8', '.mp4', '.m4v')):
                add(candidate)
    except Exception:
        pass
    return result[:20]


# O R7AnalyzeWorker e o R7DownloadWorker da v2.0.3 consultam esta função
# dinamicamente no módulo v203; substituir o símbolo corrige análise e download.
v203._resolve_r7_candidates = _resolve_r7_candidates_v206

core.APP_VERSION = APP_VERSION
v203.APP_VERSION = APP_VERSION
v203.SIDEBAR_VERSION = SIDEBAR_VERSION
v204.APP_VERSION = APP_VERSION
v204.SIDEBAR_VERSION = SIDEBAR_VERSION
v205.APP_VERSION = APP_VERSION
v205.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v203.APP_VERSION = APP_VERSION
    v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    v204.APP_VERSION = APP_VERSION
    v204.SIDEBAR_VERSION = SIDEBAR_VERSION
    v205.APP_VERSION = APP_VERSION
    v205.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v205.main()


if __name__ == '__main__':
    main()
