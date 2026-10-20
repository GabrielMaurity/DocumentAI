# Skill de Arquitetura .NET

## Objetivo
Garantir código organizado, desacoplado,
testável e alinhado com a arquitetura definida.

## Instruções

1. Ler docs/architecture.md.
2. Respeitar as responsabilidades das camadas.
3. Criar interfaces para integrações externas.
4. Utilizar Dependency Injection.
5. Evitar regras de negócio nos Controllers.
6. Utilizar async/await em operações de I/O.
7. Aplicar CancellationToken quando adequado.
8. Centralizar tratamento de exceções.
9. Padronizar respostas HTTP.
10. Evitar dependências circulares.

## Regras de arquitetura

- API: endpoints e configuração HTTP.
- Application: orquestração e casos de uso.
- Domain: modelos e regras de negócio.
- Infrastructure: serviços externos e implementações.

## Validação

- Verificar referências entre projetos.
- Executar dotnet build.
- Identificar violações arquiteturais.
- Informar arquivos criados ou modificados.