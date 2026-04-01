# Discovery - PBINC CRM e Conciliador Financeiro

Data: 2026-04-01
Escopo Jira: `PBINC-4`, `PBINC-5`

## Regra-mãe

Os dois projetos devem se integrar ao ecossistema PinkBlue Vet e ao sistema SimplesVet, mas não devem reproduzir o que o SimplesVet já faz bem.

O papel desses módulos deve ser:

- ampliar a capacidade operacional da clínica;
- organizar camadas que hoje ficam fora ou mal resolvidas;
- consumir dados do SimplesVet como fonte importante, sem tentar substituí-lo logo de saída.

## Projeto 1 - CRM veterinário

### Problema que o projeto resolve

Clínicas costumam ter agenda, cadastro e parte do histórico dentro do sistema principal, mas não necessariamente têm uma camada forte de relacionamento, segmentação, reativação e acompanhamento comercial/operacional.

O CRM deve existir para responder perguntas como:

- quais tutores estão sumidos e deveriam ser reativados;
- quais pacientes estão entrando em jornadas específicas (retorno, pós-cirúrgico, exames pendentes, vacinas, campanhas);
- quais contatos estão engajando com a clínica;
- quais ações/comunicações geram retorno real.

### O que ele não deve ser no início

- não deve substituir prontuário;
- não deve substituir agenda/base operacional que já exista no SimplesVet;
- não deve tentar virar ERP completo;
- não deve replicar manualmente todas as telas do sistema principal.

### Proposta de recorte

Primeiro recorte recomendado:

- foco em tutor + paciente + relacionamento;
- timeline única de relacionamento;
- listas segmentadas;
- tarefas e follow-ups internos;
- gatilhos oriundos do Lab Monitor e de eventos do SimplesVet.

### MVP sugerido

- cadastro espelhado de tutores e pacientes relevantes;
- timeline simples por tutor/paciente;
- etiquetas/segmentos;
- lista de reativação;
- listas operacionais como:
  - exames liberados sem contato posterior;
  - pacientes sem retorno em X dias;
  - pacientes com jornada interrompida;
- tarefas/comentários internos por caso;
- base para mensagens/campanhas futuras, sem automação pesada no primeiro momento.

### Integração com SimplesVet

Idealmente o CRM consome do SimplesVet:

- tutores;
- pacientes;
- atendimentos/visitas;
- procedimentos/serviços;
- profissional responsável;
- situações relevantes de relacionamento.

Integração com Lab Monitor:

- status de exames;
- liberação de resultados;
- atraso/criticidade operacional;
- gatilho para follow-up clínico ou comercial.

### Sinais de que o CRM pode sair da incubadora

- fonte confiável de dados do SimplesVet definida;
- 2 ou 3 jornadas claras priorizadas;
- dono operacional da rotina de uso;
- backlog próprio além de discovery.

## Projeto 2 - Conciliador financeiro

### Problema que o projeto resolve

Mesmo quando a clínica tem lançamentos financeiros no sistema principal, costuma faltar uma camada que confronte:

- o que o sistema diz que deveria entrar;
- o que o banco/PSP adquirente realmente liquidou;
- o que ficou pendente, divergente ou sem lastro.

O conciliador deve existir para virar a camada de verdade financeira operacional.

### O que ele não deve ser no início

- não deve substituir faturamento/caixa do SimplesVet;
- não deve tentar virar ERP contábil completo;
- não deve depender de integração bancária sofisticada no primeiro corte.

### Proposta de recorte

Primeiro recorte recomendado:

- importar títulos/recebíveis do SimplesVet;
- importar extratos/arquivos externos;
- reconciliar valores esperados versus liquidados;
- destacar divergências e pendências.

### MVP sugerido

- entrada de dados do SimplesVet via exportação ou API;
- importação de extrato bancário (`CSV`, `OFX`) e, se existir, arquivos de adquirente/cartão;
- motor de conciliação com regras configuráveis;
- fila de exceções:
  - não conciliado
  - conciliado com diferença
  - liquidação pendente
  - taxa divergente
- fechamento simples por período;
- trilha de ajuste manual auditável.

### Integração com SimplesVet

O conciliador deve consumir do SimplesVet o que já existe de financeiro operacional:

- contas a receber;
- baixa/recebimento registrado;
- tipo de pagamento;
- data prevista/real;
- possível amarração com tutor/paciente/atendimento.

Ele complementa isso com:

- extrato bancário real;
- liquidação de cartão/Pix;
- taxas e atrasos;
- divergências de cadastro ou processo.

### Valor estratégico

Se o CRM amplia relacionamento, o conciliador amplia controle e verdade financeira.

Os dois juntos ajudam a PinkBlue Vet a operar melhor sem tentar reinventar o núcleo que o SimplesVet já cobre.

## Integração entre os dois projetos

Eles não precisam nascer integrados entre si, mas há sinergia futura:

- CRM pode marcar clientes com pendência/risco financeiro em fluxos específicos;
- financeiro pode usar dados de jornada/origem para entender rentabilidade;
- ambos podem compartilhar identidade de tutor/paciente e eventos-base vindos do SimplesVet.

## Ferramental e infra provável quando amadurecerem

Sem desenvolver nada agora, o desenho mais plausível é:

- ambos como módulos web separados sob o guarda-chuva PinkBlue Vet;
- banco compartilhado de plataforma com schemas/tabelas segregados, ou serviços separados quando a escala pedir;
- integração com SimplesVet via API/exportação/importação controlada;
- UI própria e backlog próprio quando saírem da incubadora.

## Perguntas em aberto para responder depois

### Sobre o SimplesVet

1. Quais entidades o SimplesVet expõe hoje com confiabilidade: tutor, paciente, atendimento, financeiro, agenda, exames?
2. Existe API oficial, exportação CSV/Excel ou apenas acesso manual?
3. O SimplesVet já cobre campanhas, relacionamento e lembretes, mesmo que de forma limitada?

### Sobre o CRM

4. O maior problema hoje é reativação, acompanhamento de jornadas, campanhas, pós-atendimento ou organização do time?
5. Quais canais fazem mais sentido depois: WhatsApp, email, telefone, tarefas internas?
6. O CRM deve olhar mais para tutor, para paciente ou para ambos com a mesma importância?

### Sobre o conciliador financeiro

7. Quais meios de pagamento precisam entrar primeiro: banco, Pix, cartão, dinheiro, boleto?
8. O maior valor esperado está em conciliação bancária, taxas de adquirente, fechamento de caixa ou auditoria de recebíveis?
9. Existe hoje algum processo manual que já funciona parcialmente e pode virar a base do MVP?

## Fontes de contexto usadas

- contexto local do repositório PinkBlue Vet / Lab Monitor
- backlog atual de `PBINC`
- restrição funcional informada pelo usuário: integrar com SimplesVet sem duplicar o que ele já faz
