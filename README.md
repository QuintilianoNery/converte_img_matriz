# Conversor de Imagem para Matriz de Bordado (PES/DST/JEF/EXP/HUS/VP3)

Este projeto oferece uma interface web para:

- selecionar uma imagem;
- definir tamanho final (10/20/30 cm);
- escolher formato de saída (PES/DST/JEF/EXP/HUS/VP3);
- ajustar quantidade de cores e nível de detalhe;
- executar perfuração automática e editar objetos;
- gerar preview e baixar a matriz final.

## Arquitetura

- Frontend: `index.html`, `css/`, `js/` (na raiz do projeto)
- Backend: `server/` (FastAPI + conversão + preview + download)

## Rodar local no Windows (rápido)

1. Execute `rodar_local.bat` na raiz do projeto.
2. Aguarde instalar dependências e iniciar o servidor.
3. Abra `http://127.0.0.1:8000`.

## Rodar local (modo manual)

### Requisitos

- Python 3.11+

### Comandos

```bat
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Abra no navegador: `http://127.0.0.1:8000`.

## Configuração de API no frontend

Arquivo: `js/app.js`

Constante: `DEFAULT_API_BASE_URL`

Exemplos:

- Local: `http://127.0.0.1:8000`
- Hospedado: `https://seu-backend.exemplo.com`

## Qualidade da conversão

A conversão automática foi otimizada para produtividade, mas ainda é um processo assistido (não substitui 100% o digitizing manual avançado em todos os cenários).

Para melhores resultados:

- use imagem com boa resolução e contraste;
- prefira preset `medio` ou `premium_clean` como ponto de partida;
- revise objetos críticos antes da conversão final.
