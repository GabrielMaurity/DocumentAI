# Skill de Publicação no Azure

## Objetivo
Padronizar o processo de publicação
de aplicações ASP.NET Core no Azure.

## Instruções

1. Identificar o projeto ASP.NET Core principal.
2. Confirmar que a aplicação compila.
3. Executar os testes automatizados.
4. Preparar o artefato de publicação.
5. Criar workflow do GitHub Actions.
6. Separar etapas de Build, Test e Deploy.
7. Utilizar autenticação federada OIDC.
8. Utilizar secrets e variáveis de ambiente.
9. Nunca incluir credenciais no repositório.
10. Validar a aplicação após o deploy.

## Segurança

- Aplicar princípio do menor privilégio.
- Não imprimir segredos nos logs.
- Exigir aprovação para alterações no Azure.
- Não publicar se os testes falharem.
- Não substituir configurações de produção
  sem autorização.

## Validação

- Confirmar sucesso do workflow.
- Verificar o endpoint de Health Check.
- Validar logs e inicialização.
- Registrar falhas identificadas.
- Sugerir rollback se necessário.