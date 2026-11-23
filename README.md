# Stem Splitter

Separa músicas em pistas (voz, bateria, baixo, guitarra, piano, outros) com IA, 100% local no Mac, e abre num mixer multipista com mute, solo, volume, loop A–B e exportação da mix.

## Instalar

Requer [uv](https://docs.astral.sh/uv/) e ffmpeg (`brew install uv ffmpeg`).

```sh
uv sync
```

## Abrir

```sh
./start.sh
```

Sobe o servidor em `http://127.0.0.1:8765` (prioridade baixa, para não travar o Mac) e abre o navegador.

- Músicas e pistas: `~/Music/StemSplitter/songs`
- Modelos de IA (baixados na 1ª vez): `~/Music/StemSplitter/models`
- Log: `~/Music/StemSplitter/server.log`

## Modos

| Modo | Modelo | Pistas |
|---|---|---|
| Voz + Instr. | htdemucs (bateria + baixo + outros somados) | 2 |
| 4 pistas | htdemucs | 4 |
| 6 pistas | htdemucs_6s | 6 |

Alternativas mais pesadas/melhores (para Macs com mais RAM) estão comentadas em `app.py`.
