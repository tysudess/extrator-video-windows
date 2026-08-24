from pathlib import Path
import shutil, re, json, os, py_compile

ROOT = Path(__file__).resolve().parent
SRC = ROOT
OUT = ROOT / 'ubuntu_src'
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for name in ('main.py','advanced_editor.py','range_slider.py','requirements.txt'):
    shutil.copy2(SRC/name, OUT/name)

p = OUT/'main.py'
s = p.read_text(encoding='utf-8')
s = s.replace('import re\nimport subprocess', 'import re\nimport socket\nimport ssl\nimport subprocess')
s = s.replace("APP_VERSION = 'Windows Portable v1.9.12 — Future UI — Timeline + compressão inteligente'",
              "APP_VERSION = 'Ubuntu Portable v1.9.13 — Future UI — Timeline + compressão inteligente'")
s = s.replace("YTDLP_EXE = BIN_DIR / 'yt-dlp.exe'", "YTDLP_EXE = BIN_DIR / 'yt-dlp'")
s = s.replace("FFMPEG_EXE = BIN_DIR / 'ffmpeg.exe'", "FFMPEG_EXE = BIN_DIR / 'ffmpeg'")
s = s.replace("FFPROBE_EXE = BIN_DIR / 'ffprobe.exe'", "FFPROBE_EXE = BIN_DIR / 'ffprobe'")
s = s.replace("DENO_EXE = BIN_DIR / 'deno.exe'", "DENO_EXE = BIN_DIR / 'deno'")
s = s.replace('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Mozilla/5.0 (X11; Linux x86_64)')
s = s.replace("default = {'ATIVADO': False, 'SERVIDOR': '', 'PORTA': ''}",
              "default = {'ATIVADO': True, 'SERVIDOR': 'proxy-7dn.mb', 'PORTA': '6060'}")
s = s.replace("return 'A rede bloqueou a conexão por certificado. Pode ser necessário instalar o certificado CA corporativo no Windows.'",
              "return ('Falha de certificado HTTPS. Esta versão usa os certificados do Ubuntu. ' 'Se continuar, envie ultimo-erro-yt-dlp.txt para análise.')")
s = s.replace('yt-dlp.exe não encontrado na pasta bin.', 'yt-dlp não encontrado na pasta bin.')
s = s.replace('ffmpeg.exe não encontrado na pasta bin.', 'ffmpeg não encontrado na pasta bin.')
s = s.replace('# O yt-dlp.exe oficial já traz o EJS necessário. Deno é usado apenas como runtime.',
              '# O yt-dlp portátil já traz o EJS necessário. Deno é usado apenas como runtime.')
s = s.replace('# Compatibilidade com portables antigos sem ffprobe.exe.', '# Compatibilidade com portables sem ffprobe.')

proxy_env = r'''\n\ndef proxy_environment(proxy_url=''):\n    \"\"\"Ambiente para yt-dlp/Deno/FFmpeg usando proxy e certificados do Ubuntu.\"\"\"\n    env = os.environ.copy()\n    keys = ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')\n    if proxy_url:\n        for key in keys: env[key] = proxy_url\n        env['NO_PROXY'] = env.get('NO_PROXY', 'localhost,127.0.0.1,::1')\n        env['no_proxy'] = env.get('no_proxy', 'localhost,127.0.0.1,::1')\n    else:\n        for key in keys: env.pop(key, None)\n    system_ca = Path('/etc/ssl/certs/ca-certificates.crt')\n    if system_ca.exists():\n        env['SSL_CERT_FILE'] = str(system_ca)\n        env['REQUESTS_CA_BUNDLE'] = str(system_ca)\n        env['CURL_CA_BUNDLE'] = str(system_ca)\n    env['DENO_TLS_CA_STORE'] = 'system'\n    return env\n'''
if 'def proxy_environment(' not in s:
    s = s.replace('\ndef friendly_network_error(text):\n', proxy_env+'\ndef friendly_network_error(text):\n', 1)

old = """        cmd = [
            str(YTDLP_EXE), '--no-playlist', '--newline', '--progress', '--windows-filenames',
"""
new = """        cmd = [
            str(YTDLP_EXE), '--compat-options', 'no-certifi',
            '--no-playlist', '--newline', '--progress', '--windows-filenames',
"""
if old not in s: raise RuntimeError('Estrutura do comando yt-dlp mudou; conversão interrompida.')
s = s.replace(old,new,1)

popen_old = """            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags,
            )
"""
popen_new = """            self._process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace', creationflags=flags,
                env=proxy_environment(self.proxy_url),
            )
"""
if popen_old not in s: raise RuntimeError('Popen do download não encontrado.')
s = s.replace(popen_old,popen_new,1)
if popen_old in s: s = s.replace(popen_old,popen_new,1)

s = s.replace("cmd = [str(YTDLP_EXE), '--update-to', 'nightly']",
              "cmd = [str(YTDLP_EXE), '--compat-options', 'no-certifi', '--update-to', 'nightly']")
run_old = """            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
"""
run_new = """            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=proxy_environment(self.proxy_url),
            )
"""
if run_old not in s: raise RuntimeError('Atualizador yt-dlp não encontrado.')
s = s.replace(run_old,run_new,1)

proxy_worker = r'''\n\nclass ProxyTestWorker(QThread):\n    done = Signal(str)\n    failed = Signal(str)\n    def __init__(self, proxy_url=''):\n        super().__init__(); self.proxy_url = proxy_url or ''\n    def run(self):\n        lines=[]\n        try:\n            parsed=urllib.parse.urlsplit(self.proxy_url); host,port=parsed.hostname,parsed.port\n            if not host or not port: raise RuntimeError('Endereço do proxy inválido.')\n            lines.append(f'Proxy: {host}:{port}')\n            infos=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)\n            lines.append('DNS: OK — '+', '.join(sorted({x[4][0] for x in infos})[:5]))\n            with socket.create_connection((host,port),timeout=10): pass\n            lines.append('TCP: OK — porta do proxy acessível')\n            opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':self.proxy_url,'https':self.proxy_url}))\n            try:\n                with opener.open(urllib.request.Request('http://example.com/',headers={'User-Agent':'Mozilla/5.0'}),timeout=20) as r:\n                    lines.append(f'HTTP: OK — status {getattr(r,\"status\",\"?\")}')\n            except urllib.error.HTTPError as e:\n                if e.code==407: raise RuntimeError('HTTP FALHOU: proxy exige autenticação (407).')\n                lines.append(f'HTTP: resposta {e.code}')\n            try:\n                with opener.open(urllib.request.Request('https://www.youtube.com/robots.txt',headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:\n                    lines.append(f'HTTPS: OK — status {getattr(r,\"status\",\"?\")}')\n            except urllib.error.HTTPError as e:\n                if e.code==407: raise RuntimeError('HTTPS FALHOU: proxy exige autenticação (407).')\n                lines.append(f'HTTPS: resposta {e.code}')\n            except ssl.SSLCertVerificationError as e: raise RuntimeError(f'HTTPS FALHOU POR CERTIFICADO: {e}')\n            proc=subprocess.run([str(YTDLP_EXE),'--ignore-config','--compat-options','no-certifi','--version'],capture_output=True,text=True,timeout=60,env=proxy_environment(self.proxy_url))\n            if proc.returncode!=0: raise RuntimeError(f'yt-dlp FALHOU — código {proc.returncode}')\n            ver=(proc.stdout or proc.stderr or '').strip().splitlines(); lines.append('yt-dlp: OK'+(f' — {ver[0]}' if ver else ''))\n            lines += ['', 'RESULTADO: PROXY FUNCIONANDO PARA HTTP E HTTPS.']\n            result='\\n'.join(lines); (ROOT_DIR/'teste-proxy.txt').write_text(result,encoding='utf-8'); self.done.emit(result)\n        except Exception as e:\n            lines += ['', 'RESULTADO: FALHA', str(e)]; result='\\n'.join(lines)\n            try: (ROOT_DIR/'teste-proxy.txt').write_text(result,encoding='utf-8')\n            except Exception: pass\n            self.failed.emit(result)\n'''
if 'class ProxyTestWorker' not in s:
    s=s.replace('\n\nclass UpdateWorker(QThread):\n',proxy_worker+'\n\nclass UpdateWorker(QThread):\n',1)

s=s.replace("self.proxy_server = QLineEdit(); self.proxy_server.setPlaceholderText('Ex.: proxy.empresa.local ou 10.0.0.10')",
            "self.proxy_server = QLineEdit(); self.proxy_server.setPlaceholderText('proxy-7dn.mb')")
s=s.replace("self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText('Ex.: 8080')",
            "self.proxy_port = QLineEdit(); self.proxy_port.setPlaceholderText('6060')")
ui_old="""        pr = QHBoxLayout(); self.btn_save_proxy = QPushButton('SALVAR CONFIGURAÇÃO'); self.btn_save_proxy.setProperty('role', 'primary')
        self.btn_clear_proxy = QPushButton('USAR CONEXÃO DIRETA')
        pr.addWidget(self.btn_save_proxy); pr.addWidget(self.btn_clear_proxy); pr.addStretch(1); p.addLayout(pr)
"""
ui_new="""        pr = QHBoxLayout(); self.btn_save_proxy = QPushButton('SALVAR CONFIGURAÇÃO'); self.btn_save_proxy.setProperty('role', 'primary')
        self.btn_test_proxy = QPushButton('TESTAR PROXY')
        self.btn_clear_proxy = QPushButton('USAR CONEXÃO DIRETA')
        pr.addWidget(self.btn_save_proxy); pr.addWidget(self.btn_test_proxy); pr.addWidget(self.btn_clear_proxy); pr.addStretch(1); p.addLayout(pr)
"""
if ui_old not in s: raise RuntimeError('UI de proxy não encontrada.')
s=s.replace(ui_old,ui_new,1)
s=s.replace("self.btn_save_proxy.clicked.connect(self.save_proxy_settings); self.btn_clear_proxy.clicked.connect(self.use_direct_connection)",
            "self.btn_save_proxy.clicked.connect(self.save_proxy_settings); self.btn_test_proxy.clicked.connect(self.test_proxy_connection); self.btn_clear_proxy.clicked.connect(self.use_direct_connection)",1)
method=r'''    def test_proxy_connection(self):\n        proxy=self._current_proxy_url(show_error=True)\n        if proxy is None: return\n        if not proxy:\n            QMessageBox.warning(self,APP_NAME,'O teste deve ser feito com \"Usar proxy\" selecionado.'); return\n        self.btn_test_proxy.setEnabled(False); self.proxy_status.setText('Testando proxy, DNS, HTTP e HTTPS...')\n        self.proxy_test_worker=ProxyTestWorker(proxy)\n        def ok(msg):\n            self.btn_test_proxy.setEnabled(True); self._update_proxy_status(); QMessageBox.information(self,APP_NAME,msg+'\\n\\nResultado salvo em teste-proxy.txt.')\n        def fail(msg):\n            self.btn_test_proxy.setEnabled(True); self._update_proxy_status(); QMessageBox.critical(self,APP_NAME,msg+'\\n\\nEnvie teste-proxy.txt para análise.')\n        self.proxy_test_worker.done.connect(ok); self.proxy_test_worker.failed.connect(fail); self.proxy_test_worker.start()\n\n'''
if 'def test_proxy_connection' not in s:
    s=s.replace('    def use_direct_connection(self):\n',method+'    def use_direct_connection(self):\n',1)
p.write_text(s,encoding='utf-8')

a=OUT/'advanced_editor.py'; t=a.read_text(encoding='utf-8')
t=t.replace('"""Editor de timeline portado da versão Android v1.9.10 para Windows."""','"""Editor de timeline da v1.9.13 portado para Ubuntu/Linux."""')
t=t.replace('ffmpeg.exe não encontrado na pasta bin.','ffmpeg não encontrado na pasta bin.')
a.write_text(t,encoding='utf-8')

(OUT/'config-proxy.json').write_text(json.dumps({'ATIVADO':True,'SERVIDOR':'proxy-7dn.mb','PORTA':'6060'},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Executar-ExtratorVideos.sh').write_text('''#!/usr/bin/env bash\nset -e\nDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\ncd "$DIR"\nchmod +x "$DIR/ExtratorVideos" "$DIR/bin/yt-dlp" "$DIR/bin/ffmpeg" "$DIR/bin/ffprobe" "$DIR/bin/deno" 2>/dev/null || true\nfind "$DIR/bin/yt-dlp-unpacked" -type f \\( -name yt-dlp -o -name yt-dlp_linux \\) -exec chmod +x {} \\; 2>/dev/null || true\nexport QT_MEDIA_BACKEND=ffmpeg\nexport QT_PLUGIN_PATH="$DIR/_internal/PySide6/Qt/plugins${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"\nexport QML2_IMPORT_PATH="$DIR/_internal/PySide6/Qt/qml${QML2_IMPORT_PATH:+:$QML2_IMPORT_PATH}"\nexec "$DIR/ExtratorVideos" "$@"\n''',encoding='utf-8')

readme='''EXTRATOR DE VÍDEOS — UBUNTU PORTABLE v1.9.13\nDESIGN FUTURO + TIMELINE + COMPRESSÃO INTELIGENTE\n\nPort direto da versão Windows v1.9.13 DESIGN FUTURO BUILD FIX.\nPreserva download, YouTube, qualidades, editor/timeline, corte, união, miniaturas, zoom, H.264/H.265 e compressão inteligente.\n\nCorreções Ubuntu incorporadas da base estável v1.6.3:\n- Proxy padrão proxy-7dn.mb:6060.\n- HTTP_PROXY/HTTPS_PROXY/ALL_PROXY para subprocessos.\n- yt-dlp usa --compat-options no-certifi e certificados do Ubuntu.\n- Deno usa o armazenamento TLS do sistema.\n- Teste de proxy integrado.\n- A verificação HTTPS continua ativada.\n\nO GitHub Actions empacota yt-dlp, Deno e FFmpeg/FFprobe estáticos para Linux x86_64.\nCompatível com Ubuntu 22.04/24.04 x86_64.\n'''
(OUT/'LEIA-ME.txt').write_text(readme,encoding='utf-8')

for f in ('main.py','advanced_editor.py','range_slider.py'):
    py_compile.compile(str(OUT/f),doraise=True)
for d in OUT.rglob('__pycache__'): shutil.rmtree(d)
print('Ubuntu source generated:',OUT)
