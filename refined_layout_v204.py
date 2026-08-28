import refined_layout_v203 as v203

APP_VERSION = 'Windows Portable v2.0.4 — R7 Selection Fix + R7 Player Fix + Sessão Globoplay Persistente'
SIDEBAR_VERSION = 'v2.0.4  •  R7 SELECTION FIX'

core = v203.core


_original_analysis_finished = core.MainWindow.analysis_finished


def analysis_finished_v204(self, data):
    """Mantém o link original da matéria R7 como referência da análise.

    A v2.0.3 resolve a página do R7 para uma URL interna HLS/MP4 antes de
    consultar as qualidades. O resultado do analisador, porém, carregava essa
    URL interna em analyzed_input_url. A tela de Download compara esse campo
    com o link que continua visível no campo de URL; por isso uma qualidade
    aparecia marcada, mas BAIXAR dizia que era necessário analisar novamente.

    Nesta correção preservamos a mídia interna apenas como diagnóstico e
    registramos o URL original da matéria como analyzed_input_url.
    """
    if isinstance(data, dict):
        current_url = self.url_edit.text().strip()
        if v203._is_r7_url(current_url):
            fixed = dict(data)
            resolved_url = str(fixed.get('analyzed_input_url') or '').strip()
            if resolved_url and resolved_url != current_url:
                fixed['r7_resolved_media_url'] = resolved_url
            fixed['analyzed_input_url'] = current_url
            data = fixed
    return _original_analysis_finished(self, data)


core.MainWindow.analysis_finished = analysis_finished_v204
core.APP_VERSION = APP_VERSION
v203.APP_VERSION = APP_VERSION
v203.SIDEBAR_VERSION = SIDEBAR_VERSION


def main():
    core.APP_VERSION = APP_VERSION
    v203.APP_VERSION = APP_VERSION
    v203.SIDEBAR_VERSION = SIDEBAR_VERSION
    return v203.main()


if __name__ == '__main__':
    main()
