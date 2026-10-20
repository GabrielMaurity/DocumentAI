# DocumentAI - Instruções para Agentes

## Contexto
API corporativa ASP.NET Core para análise inteligente
de documentos utilizando OpenAI.

## Stack
- .NET 10
- ASP.NET Core Web API
- OpenAI SDK
- xUnit
- GitHub Actions
- Azure App Service

## Arquitetura
Utilizar os projetos:
- DocumentAI.API
- DocumentAI.Application
- DocumentAI.Domain
- DocumentAI.Infrastructure
- DocumentAI.Tests

Respeitar as dependências descritas em
docs/architecture.md.

## Regras obrigatórias
1. Ler os documentos em docs/ antes de implementar.
2. Implementar somente requisitos aprovados.
3. Utilizar Dependency Injection.
4. Utilizar async/await para operações de I/O.
5. Utilizar CancellationToken quando aplicável.
6. Não colocar regras de negócio nos Controllers.
7. Não armazenar API Keys no código-fonte.
8. Criar testes para novas funcionalidades.
9. Executar build e testes antes de concluir.
10. Não realizar deploy sem autorização.

## Fluxo de trabalho
1. Analisar os requisitos.
2. Identificar as tarefas.
3. Aplicar as Agent Skills relevantes.
4. Implementar o código.
5. Executar os testes.
6. Revisar as alterações.
7. Informar o resultado.

## Restrições
- Não alterar requisitos sem autorização.
- Não adicionar tecnologias desnecessárias.
- Não inventar credenciais.
- Não executar comandos destrutivos.
- Não modificar recursos Azure sem aprovação.