# Skill de Testes Automatizados .NET

## Objetivo
Garantir que os requisitos implementados
sejam verificados por testes automatizados.

## Instruções

1. Ler docs/requirements.md.
2. Ler docs/specifications.md.
3. Identificar os critérios de aceite.
4. Criar testes usando xUnit.
5. Utilizar mocks para serviços externos.
6. Não fazer chamadas reais à OpenAI nos
   testes unitários.
7. Criar cenários positivos e negativos.
8. Testar validações e exceções.
9. Utilizar testes de integração quando necessário.
10. Executar dotnet test.

## Convenções

- Nomear testes de forma descritiva.
- Organizar testes por serviço ou endpoint.
- Evitar dependência entre testes.
- Garantir resultados reproduzíveis.

## Validação

- Executar todos os testes.
- Informar quantidade de testes aprovados.
- Identificar falhas.
- Corrigir problemas apenas após análise.
- Não mascarar falhas removendo testes.