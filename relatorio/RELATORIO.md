# Relatório Técnico

## 1. Identificação

- Disciplina: Programação Concorrente
- Atividade: Aplicador de filtro em imagem de forma paralela
- Repositório: `unieuro-concorrente-202601-atividade4`
- Integrantes: preencher

## 2. Objetivo

Implementar uma solução de paralelização externa para converter uma imagem PPM em escala de cinza sem modificar o programa original `conversoremescalacinza.py`, executando experimentos com `2`, `4`, `8` e `12` threads.

## 3. Solução proposta

A abordagem escolhida divide a imagem em faixas horizontais. Cada faixa é processada por uma instância separada do conversor serial original.

Para manter o conversor como caixa-preta e, ao mesmo tempo, evitar duplicação de arquivos temporários gigantescos, foi implementado um mecanismo externo de virtualização de I/O:

- cada subprocesso lê apenas sua fatia da imagem original, apresentada como um PPM independente;
- cada subprocesso grava diretamente no deslocamento correto do arquivo PPM final;
- o código original do conversor permanece intacto.

## 4. Metodologia de execução

1. Gerar a imagem de entrada com `geradorimagem.py`.
2. Executar o baseline serial com `conversoremescalacinza.py`.
3. Executar a versão paralela com `2`, `4`, `8` e `12` threads usando `paralelizador_externo.py`.
4. Validar cada saída paralela contra a saída serial usando `comparar_arquivos.py`.
5. Consolidar os tempos com `executar_experimentos.py`.

## 5. Resultados

### 5.1. Validação funcional local

A implementação foi validada localmente com uma imagem reduzida, adequada ao espaço disponível no ambiente de desenvolvimento.

Arquivo usado na validação local:

- Dimensões: `8192 x 8192`
- Tamanho estimado: `192 MiB`
- Resultado: todas as saídas paralelas foram validadas como idênticas à saída serial

| Configuração | Tempo (s) | Speedup | Eficiência |
| --- | ---: | ---: | ---: |
| Serial | 0,6263 | 1,0000 | 1,0000 |
| Paralelo 2 threads | 0,4100 | 1,5275 | 0,7638 |
| Paralelo 4 threads | 0,4388 | 1,4271 | 0,3568 |
| Paralelo 8 threads | 0,4844 | 1,2930 | 0,1616 |
| Paralelo 12 threads | 0,6798 | 0,9213 | 0,0768 |

### 5.2. Tabela para execução oficial

| Configuração | Tempo (s) | Speedup | Eficiência |
| --- | ---: | ---: | ---: |
| Serial | preencher | 1,00 | 1,00 |
| Paralelo 2 threads | preencher | preencher | preencher |
| Paralelo 4 threads | preencher | preencher | preencher |
| Paralelo 8 threads | preencher | preencher | preencher |
| Paralelo 12 threads | preencher | preencher | preencher |

## 6. Análise

Na validação local, `2` threads apresentaram o melhor resultado. A partir de `4` threads, o ganho começou a cair e, em `12` threads, o custo de orquestração e a competição por recursos superaram o benefício do paralelismo para esse tamanho de imagem. Isso é coerente com a limitação de I/O e com o overhead de subir múltiplos subprocessos do conversor.

No cenário oficial com `16 GiB`, a tendência pode mudar, pois o custo fixo da orquestração passa a ser menor em relação ao volume total de processamento. Ainda assim, o comportamento final dependerá de CPU, RAM, SSD e largura de banda de leitura e escrita disponíveis na máquina usada para a medição.

## 7. Limitações encontradas

- A imagem oficial da atividade possui aproximadamente `16 GiB`.
- Além da entrada, o experimento também demanda espaço para a saída serial e para as saídas paralelas enquanto a medição estiver em andamento.
- No ambiente usado para preparar esta entrega havia apenas `11 GiB` livres, o que impossibilitou executar localmente o experimento oficial completo.

## 8. Conclusão

A solução atende ao requisito principal da atividade: paralelizar externamente a execução do `conversoremescalacinza.py` sem alterar o programa original. O projeto também inclui automação para benchmark, validação binária das saídas e documentação para repetição do experimento oficial.
