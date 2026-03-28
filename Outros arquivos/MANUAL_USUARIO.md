# Manual do Usuario - Conversor de Imagem para Matriz de Bordado

Este manual explica, de forma pratica, como usar a ferramenta para converter imagens em arquivos de bordado (PES, DST, JEF, EXP, VP3, HUS), com perfuracao automatica e ajustes por objeto.

## 1. Objetivo da ferramenta

A ferramenta foi criada para:

- transformar imagem em matriz de bordado rapidamente;
- automatizar uma base tecnica inicial (auto punch);
- permitir ajustes finos por objeto (cor, preenchimento, densidade, compensacao, sob-costura);
- gerar arquivos prontos para teste em maquina.

## 2. Principais funcionalidades

- Conversao de imagem para matriz de bordado.
- Perfuracao automatica (analise e separacao por objetos).
- Edicao objeto por objeto.
- Ajuste rapido global (aplicar em todos os objetos).
- Presets de qualidade:
  - `leve`
  - `medio`
  - `premium`
  - `premium_clean`
- Contorno automatico por objeto.
- Estrategia automatica para preenchimento padrao: satin na borda + tatami no miolo.
- Densidade adaptativa por tamanho de objeto.
- Suavizacao de contorno vetorial para reduzir ruido.
- Preview e download do arquivo final.

## 3. Requisitos

- Windows com Python 3.11+ (ou 3.12, conforme ambiente).
- Dependencias instaladas em `server/.venv`.
- Navegador moderno (Chrome, Edge, Firefox).

## 4. Como iniciar (modo simples)

1. Execute `rodar_local.bat` na raiz do projeto.
2. Aguarde o backend iniciar.
3. Abra no navegador:
   - `http://127.0.0.1:8000/docs`

## 5. Fluxo de uso (3 passos)

## Passo 1 - Configuracao base

No formulario principal, selecione:

- Imagem.
- Tamanho final (cm).
- Formato de saida (`PES`, `DST`, `JEF`, `EXP`, `VP3`, `HUS`).
- Quantidade de cores.
- Nivel de detalhe (`low`, `medium`, `high`).
- Preset de qualidade (`leve`, `medio`, `premium`, `premium_clean`).

## Passo 2 - Perfuracao automatica

1. Clique em `Perfuracao automatica`.
2. O sistema cria objetos editaveis por area/cor.
3. Edite os objetos no painel:
   - `enabled` (ativa/desativa objeto)
   - `color`
   - `fill_type`
   - `density`
   - `shrink_comp_mm`
   - `underlay`

### Ajuste rapido global

Use o painel `Ajuste rapido global` para aplicar em massa:

- tipo de preenchimento;
- densidade;
- sob-costura;
- compensacao.

Depois clique em `Aplicar em todos`.

### Busca e organizacao

- Use o campo de busca para localizar objetos por ID (ex: `c3_o2`).
- Use `Expandir tudo` e `Recolher tudo` para navegar mais rapido.

## Passo 3 - Converter

1. Clique em `Converter`.
2. Aguarde o processamento.
3. Confira o preview.
4. Clique em `Baixar arquivo` para salvar a matriz.

## 6. Presets de qualidade (quando usar)

- `leve`:
  - menos pontos;
  - mais rapido;
  - ideal para testes e rascunho.

- `medio`:
  - equilibrio entre qualidade e tamanho de arquivo;
  - recomendado para uso geral.

- `premium`:
  - mais densidade e acabamento tecnico;
  - maior numero de pontos.

- `premium_clean`:
  - qualidade alta com menor sobreposicao de contorno;
  - reduz excesso de pontos em bordas.

## 7. Tipos de preenchimento disponiveis

- `tatami` (padrao)
- `satin`
- `prog_fill`
- `ornamental`
- `cross`
- `concentric`
- `radial`
- `spiral`
- `stipple`
- `network`
- `zigzag`

## 8. Parametros tecnicos (resumo rapido)

- `density`:
  - `low`: menos denso;
  - `medium`: balanceado;
  - `high`: mais fechado.

- `shrink_comp_mm`:
  - compensacao de encolhimento do tecido;
  - comeca em `0.4` e ajuste conforme material.

- `underlay`:
  - base de sustentacao antes do preenchimento principal;
  - `low`, `medium`, `high`.

## 9. Boas praticas para melhorar resultado

- Use imagem com boa resolucao e contraste.
- Evite detalhes minusculos para tamanhos muito pequenos.
- Comece com preset `medio` ou `premium_clean`.
- Revise objetos pequenos e bordas finas manualmente.
- Teste primeiro em tecido de amostra.

## 10. Solucao de problemas

- Preview muito escuro ou vazio:
  - verifique se a imagem nao esta totalmente transparente.

- Matriz com pontos demais:
  - use preset `premium_clean` ou `medio`;
  - reduza densidade para `medium` ou `low` em objetos grandes.

- Bordas pesadas:
  - reduza `underlay`;
  - reduza `shrink_comp_mm`;
  - use `premium_clean`.

- Erro ao converter:
  - confirme se o backend esta rodando em `http://127.0.0.1:8000`;
  - confira o campo `API (backend)` no formulario.

## 11. Limites atuais

- O processo e auto-digitizing assistido.
- Ainda nao substitui 100% digitalizacao manual avancada em todos os casos.
- Resultados podem variar conforme tecido, estabilizador, agulha, linha e maquina.

## 12. Dica final de uso

Fluxo recomendado para rotina:

1. `premium_clean` para primeira geracao.
2. Perfuracao automatica.
3. Ajuste global rapido.
4. Revisao de objetos criticos (olhos, bordas, detalhes pequenos).
5. Conversao final e teste em amostra.
