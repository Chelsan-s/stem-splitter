# 🎚️ Stem Splitter

Separe qualquer música em pistas — **voz, bateria, baixo, guitarra, piano e outros** — usando IA, **100% no seu Mac**, sem enviar nada para a internet. As pistas abrem num **mixer multipista** onde você pode tocar tudo junto, mutar, deixar em solo, ajustar o volume de cada uma, repetir um trecho (loop A–B) e exportar a sua própria mix.

Feito para músicos: tirar a voz para cantar por cima, tirar o baixo para tocar junto, estudar uma linha de bateria isolada, etc.

---

## ✅ Requisitos

- Mac com chip **Apple Silicon** (M1, M2, M3, M4…)
- macOS 13 ou mais recente
- **8 GB de RAM** ou mais (16 GB deixa bem mais rápido)
- ~**3 GB livres** no disco (programa + modelos de IA)
- Internet só na instalação e na primeira separação (para baixar os modelos)

---

## 📦 Instalação (passo a passo)

Tudo é feito no app **Terminal** (abra com `Cmd + Espaço`, digite "Terminal" e aperte Enter). Copie e cole cada comando e aperte Enter.

### 1. Instale o Homebrew (se ainda não tiver)

O Homebrew é o instalador de programas mais usado no Mac. Veja se já tem:

```sh
brew --version
```

Se aparecer "command not found", instale seguindo as instruções em **https://brew.sh** (é um único comando copiado de lá). No final, ele pode pedir para rodar 2 comandos extras — rode-os.

### 2. Instale as ferramentas necessárias

```sh
brew install uv ffmpeg git
```

- **uv** — gerencia o Python e as bibliotecas do projeto
- **ffmpeg** — lê os arquivos de áudio (MP3, M4A, WAV…)
- **git** — baixa o projeto

### 3. Baixe o projeto

```sh
cd ~/Documents
git clone https://github.com/Chelsan-s/stem-splitter.git
cd stem-splitter
```

### 4. Instale as dependências

```sh
uv sync
```

Isso baixa o Python e as bibliotecas de IA (~1–2 GB). Pode levar alguns minutos.

### 5. Abra o programa

```sh
./start.sh
```

O navegador abre sozinho em **http://127.0.0.1:8765**. Pronto! 🎉

> Na **primeira separação**, o modelo de IA é baixado automaticamente (~80 MB). Nas próximas já começa direto.

---

## 🖱️ Criar um ícone para abrir com dois cliques (opcional)

Para não precisar do Terminal toda vez, rode isto **uma vez** dentro da pasta do projeto:

```sh
osacompile -o /Applications/"Stem Splitter.app" \
  -e "do shell script \"/bin/zsh '$(pwd)/start.sh' > /dev/null 2>&1\""
```

Agora o **Stem Splitter** aparece na página de **Apps** (Launchpad) e na pasta Aplicativos. Arraste o ícone para o Dock e abra com um clique.

---

## 🎵 Como usar

### Separar uma música

1. Escolha o modo em **Separar em**:
   - **Voz + Instr.** — 2 pistas: voz e todo o resto
   - **4 pistas** — voz, bateria, baixo, outros
   - **6 pistas** — voz, bateria, baixo, guitarra, piano, outros
2. **Arraste a música** para a caixa "Arraste uma música" (ou clique nela para escolher o arquivo).
3. Um painel mostra o progresso: etapa, porcentagem e tempo restante.
4. Quando termina, o mixer abre sozinho. A música fica salva na **Biblioteca** — não precisa separar de novo.

Pode enviar várias músicas: elas entram numa fila e são processadas uma por vez.

### Mixer

| Controle | O que faz |
|---|---|
| ▶ / ⏸ (ou **barra de espaço**) | Tocar / pausar |
| ■ | Voltar ao início |
| **M** | Muta a pista |
| **S** | Solo — toca só as pistas em solo |
| Slider da pista | Volume da pista (duplo clique volta para 100%) |
| Clique na forma de onda ou na régua | Pula para aquele ponto |
| **Arrastar** na forma de onda | Marca um trecho para repetir (loop) |
| **A** / **B** | Marca início/fim do loop no ponto atual |
| **Loop** / ✕ | Liga/desliga o loop / apaga o loop |
| 🔊 | Volume geral |
| **Exportar mix** | Baixa um `.wav` exatamente com o que está tocando (ex.: a música sem o baixo) |

### Tempo de processamento

Varia com o Mac e com o que mais está aberto. Como referência, num MacBook Air M1 de 8 GB uma música de ~6 min levou de **5 a 16 minutos** no modo de 4 pistas. Para ficar mais rápido, feche apps pesados (principalmente navegador com muitas abas) enquanto separa — ou deixe rodando à noite.

A separação roda em **prioridade baixa** de propósito, para o Mac não travar enquanto você usa outras coisas.

---

## 📁 Onde ficam os arquivos

| O quê | Onde |
|---|---|
| Músicas e pistas separadas (FLAC) | `~/Music/StemSplitter/songs/` |
| Modelos de IA | `~/Music/StemSplitter/models/` |
| Log do servidor | `~/Music/StemSplitter/server.log` |

Para apagar uma música, passe o mouse sobre ela na Biblioteca e clique no **✕**.

---

## 🔧 Manutenção

**Parar o programa** (ele continua rodando em segundo plano depois de fechar o navegador):

```sh
pkill -f "uvicorn app:app"
```

**Atualizar para a versão mais nova:**

```sh
cd ~/Documents/stem-splitter
git pull
uv sync
pkill -f "uvicorn app:app"; ./start.sh
```

**Desinstalar:**

```sh
pkill -f "uvicorn app:app"
rm -rf ~/Documents/stem-splitter /Applications/"Stem Splitter.app"
rm -rf ~/Music/StemSplitter   # ⚠️ apaga também todas as músicas separadas
```

---

## ❓ Problemas comuns

**O Mac fica lento / o mouse trava durante a separação**
Falta de memória RAM. Feche o navegador (ou abas pesadas) e outros apps grandes enquanto separa. Com 8 GB, isso faz muita diferença.

**A página não abre**
Veja o log para entender o erro:
```sh
tail -50 ~/Music/StemSplitter/server.log
```

**"Erro" aparece na música**
Passe o mouse para ler a mensagem. Arquivos corrompidos ou formatos estranhos podem falhar — converta para MP3 ou WAV e tente de novo.

**Apaguei uma música enquanto separava e a próxima demorou para começar**
A separação em andamento termina em segundo plano antes de ir para a próxima. É uma limitação conhecida.

---

## 🧠 Por baixo do capô

- **IA de separação:** [Demucs v4](https://github.com/facebookresearch/demucs) (Meta), via [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator), rodando na GPU do Apple Silicon (Metal/MPS)
- **Servidor:** Python + FastAPI (`app.py`)
- **Mixer:** página web com Web Audio API (`static/index.html`) — todas as pistas tocam presas ao mesmo relógio, sem dessincronizar

| Modo | Modelo | Pistas |
|---|---|---|
| Voz + Instr. | `htdemucs` (bateria + baixo + outros somados) | 2 |
| 4 pistas | `htdemucs` | 4 |
| 6 pistas | `htdemucs_6s` | 6 |

Os modelos foram escolhidos para caber em Macs de 8 GB. Em Macs com 16 GB ou mais, dá para trocar por modelos mais pesados e de melhor qualidade (BS-RoFormer, `htdemucs_ft`) — estão comentados no início de `app.py`.
