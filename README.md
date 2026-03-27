# Conversor de Imagem para Matriz de Bordado (PES/DST/JEF/EXP/HUS/VP3)

Este projeto cria uma mini página (front em HTML) onde você:
- seleciona uma imagem (alta qualidade),
- escolhe o tamanho final (10/20/30 cm),
- escolhe o formato (DST/PES/JEF/EXP/HUS/VP3),
- escolhe quantidade de cores (8/12/16/24),
- escolhe o nível de detalhe (Baixo/Médio/Alto),
- clica em converter,
- vê uma prévia e faz download do arquivo.

## Importante (GitHub Pages)
O GitHub Pages **não roda Python**. Então:
- o front fica em `docs/` (Pages),
- a conversão roda no backend `server/` (FastAPI) hospedado em outro lugar (Render/Railway/Fly.io),
- ou localmente (Windows) com o `rodar_local.bat`.

---

# Rodar local no Windows 11 (super fácil)
1. Baixe o repositório como ZIP ou clone.
2. Dê **duplo clique** em `rodar_local.bat`.
3. O navegador vai abrir automaticamente.

Se o Windows pedir permissão do Firewall, permita (rede privada).

---

# Rodar local (modo manual / desenvolvedor)
## Requisitos
- Python 3.11+

## Comandos
```bat
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Abra:
- http://127.0.0.1:8000

---

# Configurar API do GitHub Pages / hospedagem
No arquivo:
- `docs/js/app.js`

Ajuste:
- `API_BASE_URL`

Exemplos:
- Local: `http://127.0.0.1:8000`
- Hospedado: `https://seu-backend.exemplo.com`

---

# Notas de Qualidade
A conversão "imagem -> bordado" aqui usa um método automático **simplificado**:
- quantiza as cores,
- cria pontos por "varredura" (linhas) dentro das áreas,
- gera trocas de cor por camada.

Isso gera arquivos válidos e uma prévia fiel ao arquivo gerado, mas não substitui totalmente um digitizing avançado (tatami/satin/underlay sofisticado).

---

# Estrutura
- `docs/` = Front (GitHub Pages)
- `server/` = Backend FastAPI (conversão + preview + download)