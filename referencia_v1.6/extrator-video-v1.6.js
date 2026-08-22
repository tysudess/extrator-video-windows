const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { spawn, spawnSync } = require('child_process');

const VERSAO = '1.6-ESCOLHA-DE-QUALIDADE';
const BASE_DIR = __dirname;
const DIR_VIDEOS = path.join(BASE_DIR, 'videos-baixados');

process.chdir(BASE_DIR);
fs.mkdirSync(DIR_VIDEOS, { recursive: true });

function testarExecutavel(comando) {
  try {
    // yt-dlp usa --version; FFmpeg/FFprobe usam -version.
    // A v1.1 usava --version para tudo, fazendo um FFmpeg válido
    // ser rejeitado como se não estivesse instalado.
    const base = path.basename(String(comando || '')).toLowerCase();
    const argumentos = (base.startsWith('ffmpeg') || base.startsWith('ffprobe'))
      ? ['-version']
      : ['--version'];

    const teste = spawnSync(comando, argumentos, {
      windowsHide: true,
      stdio: 'ignore',
      timeout: 15000
    });
    return !teste.error && teste.status === 0;
  } catch (_) {
    return false;
  }
}


function resolverComandoNoPath(nome) {
  try {
    const comandoBusca = process.platform === 'win32' ? 'where.exe' : 'which';
    const busca = spawnSync(comandoBusca, [nome], {
      windowsHide: true,
      encoding: 'utf8',
      timeout: 15000
    });

    if (busca.error || busca.status !== 0) return '';

    const linhas = String(busca.stdout || '')
      .split(/\r?\n/)
      .map(x => x.trim())
      .filter(Boolean);

    for (const linha of linhas) {
      if (fs.existsSync(linha) && testarExecutavel(linha)) {
        return path.resolve(linha);
      }
    }
  } catch (_) {}
  return '';
}

function procurarArquivoRecursivo(raiz, nomeArquivo, profundidadeMax = 10) {
  if (!raiz || !fs.existsSync(raiz)) return '';

  function caminhar(dir, nivel) {
    if (nivel > profundidadeMax) return '';
    let itens;
    try {
      itens = fs.readdirSync(dir, { withFileTypes: true });
    } catch (_) {
      return '';
    }

    for (const item of itens) {
      if (item.isFile() && item.name.toLowerCase() === nomeArquivo.toLowerCase()) {
        return path.join(dir, item.name);
      }
    }

    for (const item of itens) {
      if (!item.isDirectory()) continue;
      const achado = caminhar(path.join(dir, item.name), nivel + 1);
      if (achado) return achado;
    }

    return '';
  }

  return caminhar(raiz, 0);
}

function localizarExecutavel(nome, pacotesWinget = []) {
  // 1) Caminho normal/PATH. IMPORTANTE: retornamos o caminho absoluto.
  // Na v1.3, quando o retorno era apenas "ffmpeg", path.dirname('ffmpeg')
  // virava "." e o yt-dlp recebia --ffmpeg-location . por engano.
  const absolutoPath = resolverComandoNoPath(nome);
  if (absolutoPath) return absolutoPath;

  if (testarExecutavel(nome)) return nome;

  if (process.platform !== 'win32') return '';

  const exe = nome.toLowerCase().endsWith('.exe') ? nome : `${nome}.exe`;
  const localAppData = process.env.LOCALAPPDATA || '';
  const userProfile = process.env.USERPROFILE || '';

  const candidatos = [
    path.join(localAppData, 'Microsoft', 'WinGet', 'Links', exe),
    path.join(userProfile, 'AppData', 'Local', 'Microsoft', 'WinGet', 'Links', exe)
  ];

  for (const candidato of candidatos) {
    if (candidato && fs.existsSync(candidato) && testarExecutavel(candidato)) {
      return candidato;
    }
  }

  // 2) Em algumas instalações do WinGet, o pacote existe mas o alias/PATH não fica visível.
  const pastaPacotes = path.join(localAppData, 'Microsoft', 'WinGet', 'Packages');
  if (fs.existsSync(pastaPacotes)) {
    let pastas = [];
    try {
      pastas = fs.readdirSync(pastaPacotes, { withFileTypes: true })
        .filter(x => x.isDirectory())
        .map(x => x.name);
    } catch (_) {}

    const preferidas = [];
    const outras = [];
    for (const pasta of pastas) {
      const baixa = pasta.toLowerCase();
      if (pacotesWinget.some(prefixo => baixa.startsWith(prefixo.toLowerCase()))) {
        preferidas.push(pasta);
      } else {
        outras.push(pasta);
      }
    }

    for (const pasta of [...preferidas, ...outras]) {
      // Para não varrer todos os pacotes desnecessariamente, as pastas não preferidas
      // só entram quando o próprio nome indica relação com ffmpeg/yt-dlp.
      const baixa = pasta.toLowerCase();
      const ehPreferida = preferidas.includes(pasta);
      if (!ehPreferida && !baixa.includes('ffmpeg') && !baixa.includes('yt-dlp')) continue;

      const achado = procurarArquivoRecursivo(path.join(pastaPacotes, pasta), exe, 10);
      if (achado && testarExecutavel(achado)) return achado;
    }
  }

  return '';
}

const CAMINHO_YTDLP = localizarExecutavel('yt-dlp', ['yt-dlp.yt-dlp']);
const CAMINHO_FFMPEG = localizarExecutavel('ffmpeg', ['yt-dlp.FFmpeg', 'Gyan.FFmpeg']);

function normalizarUrlEncontrada(valor, paginaUrl) {
  if (!valor) return '';

  let texto = String(valor)
    .trim()
    .replace(/&amp;/gi, '&')
    .replace(/\\u0026/gi, '&')
    .replace(/\\u003d/gi, '=')
    .replace(/\\u002f/gi, '/')
    .replace(/\\\//g, '/');

  // Remove aspas ou escapes residuais no final.
  texto = texto.replace(/[\\"']+$/g, '').trim();

  try {
    return new URL(texto, paginaUrl).href;
  } catch (_) {
    return '';
  }
}

function ehCandidatoVideo(url) {
  const u = String(url || '').toLowerCase();
  return (
    u.includes('.mp4') ||
    u.includes('.m3u8') ||
    u.includes('.mpd') ||
    /(?:player|video|embed|stream)/i.test(u)
  );
}

function extrairCandidatosDoHtml(html, paginaUrl) {
  const candidatos = [];
  const vistos = new Set();

  function adicionar(valor, forcar = false) {
    const url = normalizarUrlEncontrada(valor, paginaUrl);
    if (!url || !/^https?:\/\//i.test(url)) return;
    if (!forcar && !ehCandidatoVideo(url)) return;
    if (vistos.has(url)) return;
    vistos.add(url);
    candidatos.push(url);
  }

  const texto = String(html || '')
    .replace(/\\u0026/gi, '&')
    .replace(/\\u003d/gi, '=')
    .replace(/\\u002f/gi, '/')
    .replace(/\\\//g, '/');

  // URLs absolutas que aparentam apontar para mídia/stream/player.
  const urlsAbsolutas = texto.match(/https?:\/\/[^\s"'<>]+/gi) || [];
  for (const url of urlsAbsolutas) adicionar(url);

  // src/content/file/href em elementos HTML, incluindo caminhos relativos.
  const reAtributo = /\b(?:src|content|file|href)\s*=\s*["']([^"']+)["']/gi;
  let match;
  while ((match = reAtributo.exec(texto))) {
    adicionar(match[1]);
  }

  // Campos comuns em JSON/JSON-LD de players e VideoObject.
  const reJson = /["'](?:contentUrl|embedUrl|videoUrl|streamUrl|file|src|url)["']\s*:\s*["']([^"']+)["']/gi;
  while ((match = reJson.exec(texto))) {
    const chaveTrecho = match[0].slice(0, 40);
    const forcar = /contentUrl|embedUrl|videoUrl|streamUrl/i.test(chaveTrecho);
    adicionar(match[1], forcar);
  }

  // Meta tags especificamente relacionadas a vídeo, mesmo sem extensão visível.
  const reMetaVideo = /<meta[^>]+(?:property|name)=["'](?:og:video(?::url|:secure_url)?|twitter:player(?::stream)?)["'][^>]+content=["']([^"']+)["'][^>]*>/gi;
  while ((match = reMetaVideo.exec(texto))) adicionar(match[1], true);

  const reMetaVideoInvertido = /<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["'](?:og:video(?::url|:secure_url)?|twitter:player(?::stream)?)["'][^>]*>/gi;
  while ((match = reMetaVideoInvertido.exec(texto))) adicionar(match[1], true);

  // Iframes podem apontar para players incorporados reconhecidos pelo yt-dlp.
  const reIframe = /<iframe[^>]+src=["']([^"']+)["'][^>]*>/gi;
  while ((match = reIframe.exec(texto))) adicionar(match[1], true);

  return candidatos.slice(0, 15);
}

async function baixarHtml(url) {
  const resposta = await fetch(url, {
    redirect: 'follow',
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36',
      'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
      'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'
    }
  });

  if (!resposta.ok) {
    throw new Error(`HTTP ${resposta.status} ao acessar a página.`);
  }

  const tipo = resposta.headers.get('content-type') || '';
  if (!tipo.includes('text/html')) return '';

  return await resposta.text();
}

function executarYtDlp(url, paginaReferer = '', opcoes = {}) {
  return new Promise((resolve) => {
    const modeloSaida = path.join(
      DIR_VIDEOS,
      '%(title).180B [%(id)s].%(ext)s'
    );

    const ehYoutubeAgora = ehYouTube(url);
    const formato = opcoes.formato || (
      ehYoutubeAgora
        ? 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
        : 'bv*+ba/b'
    );

    const args = [
      '--no-playlist',
      '--newline',
      '--progress',
      '--windows-filenames',
      '--trim-filenames', '180',
      '--continue',
      '--retries', '10',
      '--fragment-retries', '10',
      '--retry-sleep', 'http:linear=1::3',
      '--retry-sleep', 'fragment:linear=1::3',
      '--merge-output-format', 'mp4',
      '--remux-video', 'mp4',
      '-f', formato,
      '-o', modeloSaida,
      '--print', 'before_dl:__TITULO__:%(title)s',
      '--print', 'after_move:__ARQUIVO__:%(filepath)s'
    ];

    // O próprio programa já está rodando em Node. Desde yt-dlp 2025.11,
    // YouTube funciona melhor com um runtime JavaScript explícito.
    if (ehYoutubeAgora) {
      const majorNode = Number(String(process.versions.node || '0').split('.')[0]);
      if (majorNode >= 22 && process.execPath) {
        args.push('--js-runtimes', `node:${process.execPath}`);
      }
    }

    if (opcoes.forceIpv4) {
      args.push('--force-ipv4');
    }

    if (paginaReferer) {
      args.push('--referer', paginaReferer);
    }

    // Só passamos um caminho real do FFmpeg. Se por alguma razão o localizador
    // retornar apenas o nome do comando, deixamos o yt-dlp usar o PATH normalmente.
    if (CAMINHO_FFMPEG && (path.isAbsolute(CAMINHO_FFMPEG) || CAMINHO_FFMPEG.includes('\\') || CAMINHO_FFMPEG.includes('/'))) {
      args.push('--ffmpeg-location', path.dirname(CAMINHO_FFMPEG));
    }

    args.push(url);

    const processo = spawn(CAMINHO_YTDLP || 'yt-dlp', args, {
      cwd: BASE_DIR,
      windowsHide: true,
      shell: false
    });

    let stdout = '';
    let stderr = '';
    let arquivoFinal = '';
    let titulo = '';

    processo.stdout.on('data', (buffer) => {
      const texto = buffer.toString('utf8');
      stdout += texto;

      for (const linha of texto.split(/\r?\n/)) {
        if (linha.startsWith('__ARQUIVO__:')) {
          arquivoFinal = linha.slice('__ARQUIVO__:'.length).trim();
          continue;
        }
        if (linha.startsWith('__TITULO__:')) {
          titulo = linha.slice('__TITULO__:'.length).trim();
          console.log(`\nVídeo identificado: ${titulo}\n`);
          continue;
        }
        if (linha.trim()) console.log(linha);
      }
    });

    processo.stderr.on('data', (buffer) => {
      const texto = buffer.toString('utf8');
      stderr += texto;
      process.stderr.write(texto);
    });

    let resolvido = false;
    function finalizar(resultado) {
      if (resolvido) return;
      resolvido = true;
      resolve(resultado);
    }

    processo.on('error', (erro) => {
      finalizar({
        sucesso: false,
        codigo: -1,
        erro: erro.message,
        stdout,
        stderr,
        arquivoFinal,
        titulo
      });
    });

    processo.on('close', (codigo) => {
      finalizar({
        sucesso: codigo === 0,
        codigo,
        erro: codigo === 0 ? '' : (stderr.trim() || 'yt-dlp não conseguiu extrair o vídeo.'),
        stdout,
        stderr,
        arquivoFinal,
        titulo
      });
    });
  });
}

function salvarDiagnostico(url, tentativas = []) {
  try {
    const linhas = [
      `Extrator de Vídeos - ${VERSAO}`,
      `Data: ${new Date().toISOString()}`,
      `URL: ${url}`,
      `yt-dlp: ${CAMINHO_YTDLP || 'não localizado'}`,
      `FFmpeg: ${CAMINHO_FFMPEG || 'não localizado'}`,
      `Node: ${process.version}`,
      '',
    ];

    tentativas.forEach((t, i) => {
      linhas.push('='.repeat(70));
      linhas.push(`TENTATIVA ${i + 1}: ${t.rotulo || ''}`);
      linhas.push(`Código: ${t.resultado?.codigo}`);
      linhas.push('--- STDOUT ---');
      linhas.push(t.resultado?.stdout || '');
      linhas.push('--- STDERR ---');
      linhas.push(t.resultado?.stderr || '');
      linhas.push('');
    });

    const arquivo = path.join(BASE_DIR, 'ultimo-erro-yt-dlp.txt');
    fs.writeFileSync(arquivo, linhas.join('\n'), 'utf8');
    return arquivo;
  } catch (_) {
    return '';
  }
}

function ehYouTube(url = '') {
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, '');
    return host === 'youtube.com' || host.endsWith('.youtube.com') || host === 'youtu.be';
  } catch (_) {
    return false;
  }
}


const QUALIDADES = {
  '1': { chave: '360', rotulo: '360p', altura: 360 },
  '2': { chave: '480', rotulo: '480p', altura: 480 },
  '3': { chave: '720', rotulo: '720p HD', altura: 720 },
  '4': { chave: '1080', rotulo: '1080p Full HD', altura: 1080 },
  '5': { chave: 'melhor', rotulo: 'Melhor disponível', altura: null }
};

function obterQualidade(chave = 'melhor') {
  return Object.values(QUALIDADES).find(q => q.chave === String(chave)) || QUALIDADES['5'];
}

function formatoParaQualidade(chave = 'melhor', somenteArquivoUnico = false) {
  const q = obterQualidade(chave);

  if (!q.altura) {
    return somenteArquivoUnico
      ? 'b[ext=mp4]/b'
      : 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b';
  }

  const h = q.altura;
  if (somenteArquivoUnico) {
    return `b[height<=${h}][ext=mp4]/b[height<=${h}]/b`;
  }

  // Prefere MP4 + M4A e, se o site não tiver exatamente a resolução escolhida,
  // baixa a melhor disponível ATÉ esse limite para evitar falha desnecessária.
  return `bv*[height<=${h}][ext=mp4]+ba[ext=m4a]/b[height<=${h}][ext=mp4]/bv*[height<=${h}]+ba/b[height<=${h}]/b`;
}

async function escolherQualidade(rl) {
  console.log('\nEscolha a qualidade do vídeo:');
  console.log('  1 - 360p');
  console.log('  2 - 480p');
  console.log('  3 - 720p HD');
  console.log('  4 - 1080p Full HD');
  console.log('  5 - Melhor disponível');
  console.log('  0 - Cancelar este link');
  console.log('  SAIR - Encerrar o programa');

  while (true) {
    const entrada = (await perguntar(rl, 'Opção: ')).trim();

    if (/^(?:sair|exit|fechar)$/i.test(entrada)) {
      return { sair: true };
    }

    if (entrada === '0') {
      return { cancelar: true };
    }

    const qualidade = QUALIDADES[entrada];
    if (qualidade) {
      console.log(`\nQualidade escolhida: ${qualidade.rotulo}`);
      if (qualidade.altura) {
        console.log(`O programa usará a melhor versão disponível até ${qualidade.altura}p.\n`);
      } else {
        console.log('O programa tentará baixar a melhor qualidade disponível.\n');
      }
      return { ...qualidade };
    }

    console.log('Opção inválida. Digite 1, 2, 3, 4, 5, 0 ou SAIR.\n');
  }
}

async function extrairVideo(url, qualidade = 'melhor') {
  const formatoEscolhido = formatoParaQualidade(qualidade, false);
  const formatoCompatibilidade = formatoParaQualidade(qualidade, true);
  const infoQualidade = obterQualidade(qualidade);

  if (ehYouTube(url)) {
    console.log('\nLink do YouTube detectado. Iniciando tentativa principal...\n');

    const tentativas = [];

    let resultado = await executarYtDlp(url, '', {
      formato: formatoEscolhido
    });
    tentativas.push({ rotulo: `Qualidade ${infoQualidade.rotulo} / MP4 preferencial`, resultado });
    if (resultado.sucesso) return resultado;

    const erroCompleto1 = `${resultado.stderr || ''}\n${resultado.erro || ''}`;
    if (/403|forbidden/i.test(erroCompleto1)) {
      console.log('\nYouTube respondeu HTTP 403. Tentando novamente forçando IPv4...\n');
      resultado = await executarYtDlp(url, '', {
        forceIpv4: true,
        formato: formatoEscolhido
      });
      tentativas.push({ rotulo: `Qualidade ${infoQualidade.rotulo} + IPv4`, resultado });
      if (resultado.sucesso) return resultado;
    }

    const erroCompleto2 = `${resultado.stderr || ''}\n${resultado.erro || ''}`;
    if (/403|forbidden|requested format|format is not available/i.test(erroCompleto2)) {
      console.log('\nTentando modo de compatibilidade com arquivo único MP4...\n');
      resultado = await executarYtDlp(url, '', {
        forceIpv4: true,
        formato: formatoCompatibilidade
      });
      tentativas.push({ rotulo: `Compatibilidade ${infoQualidade.rotulo} / arquivo único MP4 + IPv4`, resultado });
      if (resultado.sucesso) return resultado;
    }

    const diagnostico = salvarDiagnostico(url, tentativas);
    if (diagnostico) {
      console.log(`\nDiagnóstico salvo em: ${diagnostico}`);
    }
    return resultado;
  }
  console.log('\nAnalisando a página com o extrator principal...\n');

  // 1) Primeiro deixamos o yt-dlp analisar a própria página. Ele já reconhece
  // muitos players, embeds e formatos de streaming sem precisarmos conhecer o site.
  let resultado = await executarYtDlp(url, '', { formato: formatoEscolhido });
  if (resultado.sucesso) return resultado;

  console.log('\nO método principal não encontrou um vídeo utilizável.');
  console.log('Procurando endereços de vídeo dentro do HTML da página...\n');

  // 2) Fallback para sites de notícia que expõem mp4/m3u8/iframe no HTML.
  let html = '';
  try {
    html = await baixarHtml(url);
  } catch (erro) {
    console.log(`Não foi possível analisar o HTML: ${erro.message}`);
  }

  if (!html) return resultado;

  const candidatos = extrairCandidatosDoHtml(html, url);
  if (!candidatos.length) return resultado;

  console.log(`Foram encontrados ${candidatos.length} endereço(s) possível(is) de vídeo.`);

  for (let i = 0; i < candidatos.length; i++) {
    console.log(`\nTentativa alternativa ${i + 1}/${candidatos.length}...`);
    const tentativa = await executarYtDlp(candidatos[i], url, { formato: formatoEscolhido });
    if (tentativa.sucesso) return tentativa;
  }

  return resultado;
}

async function perguntar(rl, mensagem) {
  return new Promise(resolve => rl.question(mensagem, resolve));
}

async function main() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  console.log('='.repeat(70));
  console.log(`EXTRATOR DE VÍDEOS - ${VERSAO}`);
  console.log('='.repeat(70));
  console.log('O programa ficará aberto para vários links.');
  console.log('Cole manualmente um link por vez.');
  console.log('Depois escolha: 360p, 480p, 720p, 1080p ou melhor disponível.');
  console.log('Aceita páginas de notícias e links de vídeo compatíveis.');
  console.log('Os vídeos serão salvos na pasta: videos-baixados');
  console.log('Digite SAIR quando quiser encerrar.\n');

  const temYtDlp = Boolean(CAMINHO_YTDLP);
  const temFfmpeg = Boolean(CAMINHO_FFMPEG);

  if (!temYtDlp || !temFfmpeg) {
    console.log('DEPENDÊNCIAS NÃO ENCONTRADAS:');
    if (!temYtDlp) console.log('- yt-dlp não foi encontrado.');
    if (!temFfmpeg) console.log('- FFmpeg não foi encontrado.');
    console.log('\nExecute primeiro o arquivo: INSTALAR-DEPENDENCIAS.bat');
    console.log('Depois feche esta janela e abra novamente o INICIAR-EXTRATOR-VIDEO.bat.\n');
    rl.close();
    return;
  }

  console.log(`✓ yt-dlp localizado: ${CAMINHO_YTDLP}`);
  console.log(`✓ FFmpeg localizado: ${CAMINHO_FFMPEG}`);
  const majorNode = Number(String(process.versions.node || '0').split('.')[0]);
  if (majorNode >= 22) {
    console.log(`✓ Node compatível com o runtime do YouTube: ${process.version}`);
  } else {
    console.log(`! Node ${process.version}: yt-dlp recomenda Node 22+ para o runtime do YouTube.`);
  }
  console.log('');

  async function processarUrl(url, qualidade = 'melhor') {
    if (!/^https?:\/\//i.test(url)) {
      throw new Error('Cole um link começando com http:// ou https://');
    }

    const resultado = await extrairVideo(url, qualidade);

    if (!resultado.sucesso) {
      throw new Error(
        'Não foi possível concluir o download deste vídeo. ' +
        'Se o erro for HTTP 403 no YouTube, verifique se o yt-dlp está atualizado e tente sem VPN/proxy. ' +
        'O arquivo ultimo-erro-yt-dlp.txt guarda os detalhes da tentativa.'
      );
    }

    console.log('\n' + '='.repeat(70));
    console.log('✓ VÍDEO SALVO COM SUCESSO');
    console.log(`Qualidade solicitada: ${obterQualidade(qualidade).rotulo}`);
    if (resultado.titulo) console.log(`Título: ${resultado.titulo}`);
    if (resultado.arquivoFinal) {
      console.log(`Arquivo: ${resultado.arquivoFinal}`);
    } else {
      console.log(`Pasta: ${DIR_VIDEOS}`);
    }
    console.log('='.repeat(70));
    return resultado;
  }

  try {
    while (true) {
      const entrada = await perguntar(rl, 'Cole o link do vídeo ou da página: ');
      const url = entrada.trim();

      if (!url) {
        console.log('Nenhum link informado.\n');
        continue;
      }

      if (/^(?:sair|exit|fechar)$/i.test(url)) {
        console.log('\nExtrator encerrado.');
        break;
      }

      try {
        if (!/^https?:\/\//i.test(url)) {
          throw new Error('Cole um link começando com http:// ou https://');
        }

        const escolha = await escolherQualidade(rl);
        if (escolha.sair) {
          console.log('\nExtrator encerrado.');
          break;
        }
        if (escolha.cancelar) {
          console.log('\nDownload cancelado. Cole outro link.\n');
          continue;
        }

        await processarUrl(url, escolha.chave);
        console.log('\nCole o próximo link ou digite SAIR.\n');
      } catch (erro) {
        console.error(`\nERRO: ${erro.message}`);
        console.log('O programa continuará aberto. Tente outro link ou digite SAIR.\n');
      }
    }
  } finally {
    rl.close();
  }
}

if (require.main === module) main();

module.exports = {
  extrairVideo,
  extrairCandidatosDoHtml,
  normalizarUrlEncontrada,
  ehCandidatoVideo,
  ehYouTube,
  formatoParaQualidade,
  obterQualidade,
  VERSAO
};
