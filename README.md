# Relatorio da Atividade 4 - Conversao de Imagem PPM em Escala de Cinza

**Disciplina:** Programacao Concorrente  
**Aluno(s):** Ellen, Felipe, Gustavo Barboza e Leticia  
**Turma:** ADS05.1 e SI05.1  
**Professor:** Rafael  
**Data:** 01/04/2026

---

# 1. Descricao do Problema

O problema computacional consiste em converter uma imagem PPM binaria no formato `P6` para escala de cinza. A versao original do projeto realiza esse processamento de forma serial, lendo blocos da imagem e aplicando a formula `0.299R + 0.587G + 0.114B` para gerar o novo valor de cada pixel.

A principal restricao da atividade foi manter o arquivo `conversoremescalacinza.py` intocado, tratando-o como caixa-preta. Por isso, a solucao paralela foi implementada externamente: a imagem foi particionada em faixas horizontais e cada faixa passou a ser processada por uma instancia independente do conversor serial.

Para viabilizar essa estrategia sem criar copias temporarias gigantescas da imagem, o projeto utiliza um hook externo de I/O que apresenta para cada subprocesso apenas a sua fatia da imagem como se fosse um PPM completo, ao mesmo tempo em que grava o resultado diretamente no deslocamento correto do arquivo final.

**Questoes respondidas**

* Qual e o objetivo do programa? Converter uma imagem RGB para escala de cinza.
* Qual o volume de dados processado? A execucao analisada utilizou uma imagem de `75672 x 75672`, com tamanho estimado de `16.00 GiB` e tamanho real em disco de `16.00 GiB`.
* Qual algoritmo foi utilizado? Conversao pixel a pixel para tons de cinza, com particionamento horizontal da imagem e orquestracao paralela externa.
* Qual a complexidade aproximada do algoritmo? `O(largura x altura)`, pois cada pixel e processado uma vez.

Os experimentos foram executados no cenario oficial da atividade, com a imagem PPM de aproximadamente 16 GiB gerada pelo projeto. Na versao paralela, a imagem foi repartida em `100` fatias totais.

---

# 2. Ambiente Experimental

Os testes foram executados em maquina local com os seguintes recursos:

| Item                        | Descricao |
| --------------------------- | --------- |
| Processador                 | Apple M2 |
| Numero de nucleos           | 8 (4 Performance and 4 Efficiency) |
| Memoria RAM                 | 8 GB |
| Sistema Operacional         | macOS 26.3.1 |
| Linguagem utilizada         | Python 3.9.6 |
| Biblioteca de paralelizacao | concurrent.futures.ThreadPoolExecutor + subprocessos Python |
| Compilador / Versao         | Interpretador CPython 3.9.6 |

---

# 3. Metodologia de Testes

O tempo de execucao foi medido com `time.perf_counter()`. Para reduzir distorcoes do tempo externo de inicializacao do Python, o benchmark prioriza o tempo total reportado pelos proprios scripts da conversao serial e da orquestracao paralela.

As configuracoes testadas foram:

* 1 thread/processo, correspondente a versao serial
* 2 threads/processos
* 4 threads/processos
* 8 threads/processos
* 12 threads/processos

Procedimento adotado:

* `1` execucoes para cada configuracao
* uso da media aritmetica como tempo representativo
* mesma entrada em todas as execucoes
* validacao da corretude comparando cada saida paralela com a linha de base serial
* particionamento da imagem em `100` fatias na versao paralela

Condicoes de execucao:

* testes feitos na mesma maquina local
* sem alteracao do codigo entre uma execucao e outra
* sem controle rigido de carga externa do sistema, o que explica pequenas oscilacoes entre repeticoes

Arquivos principais do projeto:

* `conversoremescalacinza.py`: execucao serial original
* `paralelizador_externo.py`: orquestracao da execucao paralela sem alterar o conversor
* `executar_experimentos.py`: automacao do benchmark e consolidacao dos resultados
* `gerar_relatorio_modelo.py`: geracao automatica do relatorio, planilhas e graficos

Planilhas geradas automaticamente:

* [Tempos Medios](planilhas/tempos_medios.csv)
* [Metricas Consolidadas](planilhas/metricas.csv)
* [Execucoes Detalhadas](planilhas/execucoes_detalhadas.csv)

---

# 4. Resultados Experimentais

Tempos medios de execucao medidos em segundos:

| Nº Threads/Processos | Tempo de Execucao (s) |
| -------------------- | --------------------- |
| 1 | 109.7100 |
| 2 | 104.5300 |
| 4 | 70.5900 |
| 8 | 128.1600 |
| 12 | 251.5200 |

Observacao: o melhor tempo absoluto foi obtido com `4` threads/processos.

---

# 5. Calculo de Speedup e Eficiencia

## Formulas Utilizadas

### Speedup

```text
Speedup(p) = T(1) / T(p)
```

Onde:

* `T(1)` = tempo da execucao serial
* `T(p)` = tempo com `p` threads/processos

### Eficiencia

```text
Eficiencia(p) = Speedup(p) / p
```

Onde:

* `p` = numero de threads ou processos

---

# 6. Tabela de Resultados

| Threads/Processos | Tempo (s) | Speedup | Eficiencia |
| ----------------- | --------- | ------- | ---------- |
| 1 | 109.7100 | 1.0000 | 1.0000 |
| 2 | 104.5300 | 1.0496 | 0.5248 |
| 4 | 70.5900 | 1.5542 | 0.3885 |
| 8 | 128.1600 | 0.8560 | 0.1070 |
| 12 | 251.5200 | 0.4362 | 0.0363 |

---

# 7. Grafico de Tempo de Execucao

Eixo X: numero de threads/processos  
Eixo Y: tempo medio de execucao em segundos

![Grafico Tempo Execucao](graficos/tempo_execucao.png)

---

# 8. Grafico de Speedup

Eixo X: numero de threads/processos  
Eixo Y: speedup medido, com comparacao visual com a linha ideal

![Grafico Speedup](graficos/speedup.png)

---

# 9. Grafico de Eficiencia

Eixo X: numero de threads/processos  
Eixo Y: eficiencia, com valores entre 0 e 1

![Grafico Eficiencia](graficos/eficiencia.png)

---

# 10. Analise dos Resultados

Os resultados mostram que a paralelizacao trouxe ganho real de desempenho, mas nao linear. O melhor caso foi com `4` threads/processos, reduzindo o tempo medio de `109.7100s` para `70.5900s`, com speedup de `1.5542x`.

O speedup nao ficou proximo do ideal em todas as configuracoes. O melhor aproveitamento ocorreu nas menores configuracoes paralelas, e a eficiencia passou a cair a partir de 2 threads/processos. Isso indica que o problema ainda sofre com custos relevantes de orquestracao e I/O mesmo no volume oficial.

Com `2` workers o tempo caiu apenas para `104.5300s`, muito longe da reducao ideal pela metade. Isso sugere que boa parte do tempo total continuou presa em leitura e escrita de disco, criacao dos subprocessos e sincronizacao externa das fatias, ou seja, componentes que nao escalam linearmente com apenas dobrar o paralelismo.

Com `8` workers o desempenho piorou para `128.1600s`. Apesar de a maquina reportar 8 nucleos totais, o Apple M2 combina 4 nucleos de performance e 4 de eficiencia, entao nem todos entregam o mesmo throughput. Alem disso, os `8 GB` de memoria unificada ficam pressionados quando varias instancias Python com `numpy` processam fatias grandes ao mesmo tempo.

Com `12` workers a degradacao foi forte, chegando a `251.5200s`. Nesse caso o experimento ultrapassou a quantidade total de nucleos da maquina e intensificou a pressao de memoria. No seu Mac com apenas `8 GB` de RAM, isso tende a aumentar trocas de contexto, perda de cache e possivel uso de swap, o que explica por que a configuracao ficou tao pior que `4` workers.

O numero maximo testado ultrapassa a capacidade total de nucleos reportada pela maquina: `sim`. Isso ajuda a explicar a perda de eficiencia nas configuracoes mais altas.

Os principais fatores para a perda de desempenho sao o custo de coordenar varios subprocessos, a competicao por leitura e escrita de disco, a disputa por CPU e cache, e o custo adicional de tratar o conversor original como caixa-preta sem alterar seu codigo-fonte.

Em resumo, a aplicacao apresentou escalabilidade limitada para este tamanho de entrada: os custos de orquestracao neutralizaram grande parte do beneficio do paralelismo.

---

# 11. Conclusao

O paralelismo trouxe ganho de desempenho nas melhores configuracoes paralelas, mas nao escalou de forma linear ate o limite testado. A melhor configuracao paralela observada neste ambiente foi:

* `4` threads/processos
* tempo medio de `70.5900s`
* speedup de `1.5542x`

Isso mostra que a estrategia externa de paralelizacao cumpriu o objetivo principal da atividade e preservou a corretude, mas tambem deixou claro que o custo de coordenacao e de I/O se torna dominante quando o grau de paralelismo cresce alem do ponto ideal para a maquina e para o tamanho da entrada.

No caso, a limitacao de `8 GB` de memoria no Mac teve peso importante no comportamento do experimento. Com poucos workers, como `2`, o paralelismo nao foi suficiente para compensar o custo fixo de I/O e orquestracao. Com muitos workers, como `8` e principalmente `12`, a maquina passou a disputar CPU, memoria unificada e largura de banda de disco ao mesmo tempo. Na pratica, isso significa que o experimento nao "deu errado" por erro de implementacao, mas porque o ambiente fisico passou a ser o gargalo principal.

Por isso, para esta maquina, o mais correto seria trabalhar com menos concorrencia efetiva, aproximadamente na metade das configuracoes mais agressivas, priorizando algo em torno de `2` a `4` workers ativos em vez de insistir em `8` ou `12`. Em outras palavras, aumentar o numero de workers alem desse ponto nao trouxe mais poder de processamento util; trouxe principalmente mais contenção.

Melhorias futuras possiveis:

* reduzir o overhead de coordenacao dos subprocessos
* experimentar outras granularidades de particionamento da imagem
* medir o comportamento em uma maquina com mais memoria e mais espaco para executar o cenario oficial de 16 GiB
* avaliar alternativas de paralelizacao com menos custo de inicializacao

---

# Como Executar

Gerar a imagem oficial da atividade:

```bash
python geradorimagem.py
```

Executar a conversao serial:

```bash
python conversoremescalacinza.py imagem_entrada.ppm imagem_saida.ppm
```

Executar benchmark com 2, 4, 8 e 12 threads/processos:

```bash
python executar_experimentos.py imagem_entrada.ppm --threads 2 4 8 12 --fatias 100 --repeticoes 1 --output-dir resultados/execucao_oficial_fatias100 --limpar-saidas
```

Arquivos gerados:

* `resultados/execucao_oficial_fatias100/resultados.json`
* `resultados/execucao_oficial_fatias100/resultados.csv`
* `resultados/execucao_oficial_fatias100/resultados.md`
* `relatorio/RELATORIO_PREENCHIDO.md`
* `relatorio/planilhas/*.csv`
* `relatorio/graficos/*.png`


Origem dos dados: `/Users/felipefeu/Documents/atividade01-04/resultados/execucao_oficial_fatias100/resultados.json`
