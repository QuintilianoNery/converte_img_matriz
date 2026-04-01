# Conversor de Imagem para Matriz de Bordado (PES/DST/JEF/EXP/HUS/VP3)

Este projeto oferece uma interface web para:

- selecionar imagem raster ou vetor (PNG/JPG/SVG/AI/CDR);
- definir tamanho final (10/20/30 cm);
- escolher formato de saída (PES/DST/JEF/EXP/HUS/VP3);
- ajustar quantidade de cores e nível de detalhe;
- executar perfuração automática e editar objetos;
- gerar preview e baixar a matriz final.

## Importação vetorial (.CDR/.AI/.SVG)

- O backend tenta abrir o arquivo diretamente com Pillow quando possível.
- Para vetores `.cdr`, o sistema converte primeiro para SVG e depois para PNG usando Inkscape CLI antes da análise.
- Para `.svg`, a perfuração automática lê propriedades vetoriais (formas, fill/stroke e bbox) para gerar objetos mais fiéis por elemento.
- Para rasterização de `.svg`, o backend usa `cairosvg` como caminho principal e Inkscape como fallback.
- Se o Inkscape não estiver instalado, a API retorna erro `400` com instrução clara de instalação.

Recomendação no Windows:

1. Instalar o Inkscape.
2. Garantir que `inkscape.com` esteja disponível no PATH (ou em `C:\Program Files\Inkscape\bin`).

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

Melhorias já aplicadas no motor de bordado com `pyembroidery`:

- uso de `JUMP` entre segmentos para evitar costura atravessando vazios;
- `TRIM` automático em deslocamentos longos para reduzir linhas de arraste;
- ajustes automáticos por objeto/tecido (densidade, underlay, compensações, contorno).

Para melhores resultados:

- use imagem com boa resolução e contraste;
- prefira preset `medio` ou `premium_clean` como ponto de partida;
- revise objetos críticos antes da conversão final.

## Plano de melhorias (SEO, Performance e Qualidade de Matrizes)

Este plano organiza as melhorias por prioridade para aumentar:

- descoberta orgânica (SEO);
- velocidade de processamento e resposta (performance);
- eficiência e acabamento técnico da matriz (qualidade de bordado).

### Prioridade 1 (alto impacto, baixa complexidade)

1. Agrupar objetos por cor antes de gerar trocas de linha

- Problema atual: troca de cor pode ocorrer por objeto, mesmo quando a cor se repete.
- Ganho esperado: menos trocas de linha, menor tempo de máquina, menos intervenção do operador.
- Onde atuar: [server/converter.py](server/converter.py).

2. Corrigir cálculo de segmentos longos com distância real

- Problema atual: divisão do segmento usa referência cartesiana simplificada.
- Ganho esperado: controle melhor de comprimento máximo do ponto, especialmente em diagonais.
- Onde atuar: [server/converter.py](server/converter.py).

3. Melhorar ordem de costura para reduzir deslocamentos (travel)

- Problema atual: existe jump, mas sem otimização global da sequência de segmentos.
- Ganho esperado: menos jumps, menor risco de puxadas e melhor acabamento.
- Onde atuar: [server/converter.py](server/converter.py).

4. Fechar vazamento de URL temporária no frontend

- Problema atual: alguns object URLs são criados sem liberação explícita.
- Ganho esperado: menor uso de memória em sessões longas.
- Onde atuar: [js/app.js](js/app.js).

5. SEO técnico mínimo para indexação

- Problema atual: página sem description, canonical e metadados sociais.
- Ganho esperado: melhor rastreabilidade, melhor snippet e compartilhamento social.
- Onde atuar: [index.html](index.html).

### Prioridade 2 (alto impacto, média complexidade)

1. Separar preview rápido da conversão completa

- Problema atual: o auto preview dispara a conversão completa.
- Ganho esperado: resposta mais rápida no editor e menor carga no backend.
- Estratégia:
	- criar endpoint dedicado de preview incremental no backend;
	- reutilizar análise de autopunch sempre que possível.
- Onde atuar: [server/app.py](server/app.py), [server/converter.py](server/converter.py), [js/app.js](js/app.js).

2. Validação robusta de upload

- Validar tipo MIME, extensão e tamanho máximo do arquivo.
- Retornar erro com status HTTP adequado quando inválido.
- Onde atuar: [server/app.py](server/app.py).

3. Limpeza automática de jobs antigos

- Problema atual: diretório de saída cresce indefinidamente.
- Ganho esperado: estabilidade operacional e menor uso de disco.
- Onde atuar: [server/app.py](server/app.py).

4. Padronizar retornos de erro HTTP

- Substituir respostas genéricas por HTTPException com códigos corretos.
- Exemplos: 404 para preview/download inexistente, 400 para request inválida.
- Onde atuar: [server/app.py](server/app.py).

5. Build local de assets frontend

- Substituir dependência de CDN em runtime por bundle local.
- Ganho esperado: melhor performance inicial e previsibilidade offline/local.
- Onde atuar: [index.html](index.html).

### Prioridade 3 (qualidade avançada de matriz)

1. Tie-in e tie-off automáticos por objeto

- Reduz risco de soltura de linha em início/fim de bloco.
- Onde atuar: [server/converter.py](server/converter.py).

2. Trims automáticos para jumps longos

- Melhora limpeza do bordado e reduz linhas de arraste.
- Onde atuar: [server/converter.py](server/converter.py).

3. Ângulo de preenchimento adaptativo por geometria

- Usar orientação da forma para definir direção principal de preenchimento.
- Ganho esperado: textura mais uniforme e menos enrugamento.
- Onde atuar: [server/converter.py](server/converter.py).

4. Métricas técnicas no retorno da conversão

- Incluir: total de jumps, travel total, trocas de cor, densidade média por área.
- Uso: apoiar decisão de qualidade e custo de produção.
- Onde atuar: [server/converter.py](server/converter.py), [js/app.js](js/app.js).

## SEO recomendado (checklist)

- Adicionar meta description.
- Adicionar canonical.
- Adicionar Open Graph (title, description, image, url, type).
- Adicionar Twitter Card.
- Criar robots.txt.
- Criar sitemap.xml.
- Criar página de conteúdo institucional (landing) para ranqueamento.

## Performance recomendada (checklist)

- Separar preview de baixa latência da conversão final.
- Evitar reprocessamento de imagem inteira a cada ajuste de objeto.
- Reaproveitar análise de autopunch no ciclo de edição.
- Otimizar ordem de segmentos por proximidade espacial.
- Liberar object URLs após uso no navegador.

## Qualidade de matriz recomendada (checklist)

- Reduzir trocas de cor redundantes.
- Reduzir jumps e deslocamentos longos.
- Aplicar tie-in/tie-off em pontos críticos.
- Respeitar limites de comprimento mínimo e máximo por formato.
- Melhorar direcionamento de preenchimento por objeto.

## Métricas de sucesso

Sugestão de metas para validar evolução:

- reduzir trocas de cor em 20% a 40%;
- reduzir jumps longos em 25%+;
- reduzir tempo médio de auto preview em 40%+;
- reduzir tamanho médio de arquivos em 10% a 20% (quando aplicável);
- diminuir retrabalho manual pós-conversão.

## Roadmap sugerido (execução)

Semana 1:

- SEO técnico básico (meta tags, robots, sitemap).
- correções de object URL no frontend.
- validação de upload e status HTTP padronizado.

Semana 2:

- agrupamento por cor e otimização de ordem de costura.
- correção de segmentação por distância real.

Semana 3:

- endpoint de preview incremental.
- cache de análise/autopunch para edição.

Semana 4:

- tie-in/tie-off, trims e métricas avançadas de qualidade.

---

Se quiser, posso implementar este roadmap por etapas e já abrir a Fase 1 com mudanças concretas em [index.html](index.html), [server/app.py](server/app.py) e [js/app.js](js/app.js).
