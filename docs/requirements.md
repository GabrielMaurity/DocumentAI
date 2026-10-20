# Requisitos — DocumentoAI

## 1. Visão geral

O DocumentoAI é uma API corporativa em ASP.NET Core que analisa documentos textuais com a OpenAI. O cliente envia o título e o conteúdo de um documento e recebe, em JSON estruturado, o tipo do documento, um resumo, as palavras-chave, o nível de risco e os pontos de atenção.

Este documento define **o que** o sistema deve fazer e com que qualidade. A forma de fazer fica em [architecture.md](architecture.md) e [specifications.md](specifications.md).

### 1.1 Escopo

**Incluído:**
- Análise síncrona de um documento por requisição.
- Conteúdo em texto puro, enviado no corpo da requisição.
- Endpoint de Health Check.
- Publicação no Azure App Service.

**Fora do escopo (nesta versão):**
- Upload de arquivos binários (PDF, DOCX, imagens) e OCR.
- Persistência dos documentos ou dos resultados das análises.
- Interface de usuário.
- Processamento em lote ou assíncrono (filas).
- Autenticação e autorização de clientes (ver seção 5).

### 1.2 Convenções

- **RF-xx**: requisito funcional. **RNF-xx**: requisito não funcional.
- **CA-xx.y**: critério de aceite do requisito xx. Cada critério deve poder ser verificado por um teste automatizado ou por uma inspeção objetiva.
- As palavras **deve** e **não deve** indicam obrigatoriedade.
- Rotas, nomes de campos e limites definidos aqui fazem parte do contrato e servem de base para [specifications.md](specifications.md).

---

## 2. Contrato de referência

Os critérios de aceite usam o contrato abaixo.

**Requisição:** `POST /api/documentos/analise`

```json
{
  "titulo": "Contrato de prestação de serviços de TI",
  "conteudo": "Texto completo do documento..."
}
```

**Resposta de sucesso:** `200 OK`

```json
{
  "tipoDocumento": "Contrato",
  "resumo": "Contrato de prestação de serviços de suporte de TI por 12 meses...",
  "palavrasChave": ["prestação de serviços", "SLA", "multa rescisória"],
  "nivelRisco": "MEDIO",
  "pontosAtencao": [
    "Multa rescisória de 50% do valor remanescente.",
    "Ausência de cláusula de proteção de dados (LGPD)."
  ]
}
```

**Resposta de erro:** formato Problem Details (RFC 9457), com `Content-Type: application/problem+json`.

---

## 3. Requisitos funcionais

### RF-01 — Receber documento para análise

A API deve receber, por HTTP POST, um documento com título e conteúdo textual.

| ID | Critério de aceite |
|----|--------------------|
| CA-01.1 | Um `POST /api/documentos/analise` com corpo JSON válido (`titulo` e `conteudo` preenchidos) retorna `200 OK`. |
| CA-01.2 | A API aceita `Content-Type: application/json`. Outro tipo de conteúdo retorna `415 Unsupported Media Type`. |
| CA-01.3 | Um corpo JSON malformado retorna `400 Bad Request` no formato Problem Details. |
| CA-01.4 | Os métodos `GET`, `PUT` e `DELETE` na rota de análise retornam `405 Method Not Allowed`. |
| CA-01.5 | O conteúdo é tratado como texto UTF-8. Caracteres acentuados (ex.: "ção", "é") chegam à análise sem perda ou corrupção. |

### RF-02 — Validar campos obrigatórios

A API deve validar a requisição antes de chamar a IA.

| ID | Critério de aceite |
|----|--------------------|
| CA-02.1 | Sem `titulo`, ou com `titulo` nulo, vazio ou só com espaços, a API retorna `400 Bad Request`. |
| CA-02.2 | Sem `conteudo`, ou com `conteudo` nulo, vazio ou só com espaços, a API retorna `400 Bad Request`. |
| CA-02.3 | `titulo` com mais de 200 caracteres retorna `400 Bad Request`. |
| CA-02.4 | `conteudo` com mais de 50.000 caracteres retorna `400 Bad Request`. |
| CA-02.5 | A resposta de erro de validação segue o formato Problem Details e lista, em `errors`, cada campo inválido com sua mensagem. |
| CA-02.6 | Quando há vários campos inválidos, todos aparecem na mesma resposta. |
| CA-02.7 | Quando a validação falha, nenhuma chamada é feita à OpenAI (verificável com um cliente de IA simulado nos testes). |

### RF-03 — Identificar o tipo do documento

A API deve usar IA para identificar o tipo do documento.

| ID | Critério de aceite |
|----|--------------------|
| CA-03.1 | A resposta de sucesso contém o campo `tipoDocumento`, do tipo string e não vazio. |
| CA-03.2 | Para um conjunto de documentos de referência (contrato, nota fiscal, ata de reunião, política interna, currículo), o tipo retornado corresponde à categoria esperada em pelo menos 4 dos 5 casos. |
| CA-03.3 | Para um conteúdo sem tipo reconhecível, `tipoDocumento` retorna `"Indeterminado"`, sem erro HTTP. |

### RF-04 — Gerar resumo objetivo

A API deve gerar um resumo objetivo do documento.

| ID | Critério de aceite |
|----|--------------------|
| CA-04.1 | A resposta de sucesso contém o campo `resumo`, do tipo string e não vazio. |
| CA-04.2 | O resumo tem no máximo 1.000 caracteres. |
| CA-04.3 | O resumo é escrito no mesmo idioma do documento de entrada. |
| CA-04.4 | Para documentos com mais de 1.000 caracteres, o resumo é menor que o conteúdo original. |

### RF-05 — Identificar palavras-chave

A API deve identificar as palavras-chave do documento.

| ID | Critério de aceite |
|----|--------------------|
| CA-05.1 | A resposta de sucesso contém o campo `palavrasChave`, um array de strings. |
| CA-05.2 | O array tem de 1 a 10 itens, sem itens vazios e sem itens repetidos (comparação sem diferenciar maiúsculas e minúsculas). |
| CA-05.3 | Nos documentos de referência, cada palavra-chave aparece no conteúdo ou corresponde claramente a um tema dele (verificado por inspeção). |

### RF-06 — Classificar o nível de risco

A API deve classificar o nível de risco do documento como BAIXO, MEDIO ou ALTO.

| ID | Critério de aceite |
|----|--------------------|
| CA-06.1 | A resposta de sucesso contém o campo `nivelRisco` com exatamente um dos valores `"BAIXO"`, `"MEDIO"` ou `"ALTO"` (em maiúsculas e sem acento). |
| CA-06.2 | Se a IA devolver um valor fora desse conjunto, a API não o repassa ao cliente: trata a resposta como inválida (ver RF-08). |
| CA-06.3 | Nos documentos de referência, um documento com cláusulas claramente lesivas é classificado como `"ALTO"` e um documento informativo simples é classificado como `"BAIXO"`. |

### RF-07 — Identificar pontos de atenção

A API deve identificar os pontos de atenção do documento.

| ID | Critério de aceite |
|----|--------------------|
| CA-07.1 | A resposta de sucesso contém o campo `pontosAtencao`, um array de strings. |
| CA-07.2 | O array pode estar vazio, mas nunca é nulo. Quando há itens, nenhum é vazio. |
| CA-07.3 | Quando `nivelRisco` é `"MEDIO"` ou `"ALTO"`, `pontosAtencao` tem pelo menos 1 item. |

### RF-08 — Retornar JSON estruturado

A API deve retornar o resultado da análise em JSON estruturado e previsível.

| ID | Critério de aceite |
|----|--------------------|
| CA-08.1 | A resposta de sucesso tem `Content-Type: application/json` e contém exatamente os campos `tipoDocumento`, `resumo`, `palavrasChave`, `nivelRisco` e `pontosAtencao`, em camelCase. |
| CA-08.2 | A resposta valida contra o JSON Schema publicado em [specifications.md](specifications.md). |
| CA-08.3 | Se a resposta da IA não puder ser convertida para esse contrato (JSON inválido, campo ausente ou valor fora do domínio), a API retorna `502 Bad Gateway` no formato Problem Details, sem expor o conteúdo bruto da IA. |
| CA-08.4 | Se a OpenAI estiver indisponível ou retornar erro, a API retorna `502 Bad Gateway`. Se exceder o tempo limite configurado (padrão de 60 segundos), retorna `504 Gateway Timeout`. As duas respostas seguem o formato Problem Details. |
| CA-08.5 | O contrato da API é documentado em OpenAPI e o documento fica acessível no ambiente de desenvolvimento. |

### RF-09 — Disponibilizar Health Check

A API deve disponibilizar um endpoint de Health Check.

| ID | Critério de aceite |
|----|--------------------|
| CA-09.1 | `GET /health` retorna `200 OK` com status `Healthy` quando a aplicação está em execução e configurada. |
| CA-09.2 | Quando a configuração obrigatória da OpenAI está ausente, `GET /health` retorna `503 Service Unavailable` com status `Unhealthy`. |
| CA-09.3 | O Health Check não consome tokens da OpenAI (não faz chamadas de geração de conteúdo). |
| CA-09.4 | O Health Check responde em menos de 1 segundo em condições normais. |
| CA-09.5 | O Health Check não expõe segredos, chaves ou detalhes internos de configuração. |
| CA-09.6 | O endpoint pode ser configurado como Health Check do Azure App Service. |

---

## 4. Requisitos não funcionais

### RNF-01 — Plataforma: .NET 10 e ASP.NET Core

| ID | Critério de aceite |
|----|--------------------|
| CA-N01.1 | Todos os projetos da solution `DocumentoAI.sln` têm `TargetFramework` igual a `net10.0`. |
| CA-N01.2 | A API é um projeto ASP.NET Core (`Microsoft.NET.Sdk.Web`). |
| CA-N01.3 | `dotnet build` na raiz da solution termina sem erros. |

### RNF-02 — Programação assíncrona

| ID | Critério de aceite |
|----|--------------------|
| CA-N02.1 | Toda operação de E/S (HTTP, chamadas à OpenAI) é assíncrona, com `async`/`await`. |
| CA-N02.2 | O código não usa `.Result`, `.Wait()` nem `GetAwaiter().GetResult()` (verificável por busca no código ou por analisador estático). |
| CA-N02.3 | Os métodos assíncronos recebem `CancellationToken` e o repassam até a chamada à OpenAI. |
| CA-N02.4 | Quando o cliente cancela a requisição, a chamada à OpenAI também é cancelada (verificável em teste). |

### RNF-03 — Dependency Injection

| ID | Critério de aceite |
|----|--------------------|
| CA-N03.1 | Os serviços (análise de documentos, cliente de IA, validação) são registrados no contêiner de DI nativo do ASP.NET Core. |
| CA-N03.2 | Os controllers ou endpoints dependem de abstrações (interfaces), não de implementações concretas. |
| CA-N03.3 | O cliente de IA pode ser substituído por uma implementação simulada nos testes sem alterar o código de produção. |
| CA-N03.4 | Não há criação manual (`new`) de serviços com dependências fora da composição de DI. |

### RNF-04 — Credenciais por variáveis de ambiente

| ID | Critério de aceite |
|----|--------------------|
| CA-N04.1 | A chave da OpenAI é lida da variável de ambiente `OPENAI_API_KEY` (ou da configuração equivalente do App Service). |
| CA-N04.2 | Nenhuma chave, token ou senha aparece no repositório, inclusive em `appsettings*.json` (verificável por varredura de segredos). |
| CA-N04.3 | Sem a chave configurada, a aplicação registra um erro claro na inicialização e o Health Check retorna `Unhealthy` (CA-09.2). |
| CA-N04.4 | A chave nunca aparece em logs, respostas HTTP ou mensagens de erro. |
| CA-N04.5 | O modelo da OpenAI pode ser alterado por configuração, sem recompilar. |

### RNF-05 — Tratamento centralizado de exceções

| ID | Critério de aceite |
|----|--------------------|
| CA-N05.1 | Existe um único ponto de tratamento de exceções não tratadas (middleware ou `IExceptionHandler`). |
| CA-N05.2 | Toda exceção não tratada gera uma resposta Problem Details com o status HTTP adequado: `400` para validação, `502` ou `504` para falhas da IA e `500` para erros inesperados. |
| CA-N05.3 | Em produção, as respostas de erro não contêm stack trace, nomes de classes internas ou mensagens da exceção original. |
| CA-N05.4 | Toda resposta de erro contém um `traceId` que permite localizar o registro correspondente no log. |
| CA-N05.5 | Toda exceção tratada é registrada em log com nível `Error` (falhas inesperadas) ou `Warning` (falhas esperadas, como validação). |
| CA-N05.6 | O conteúdo do documento enviado não é registrado em log. |

### RNF-06 — Testes automatizados

| ID | Critério de aceite |
|----|--------------------|
| CA-N06.1 | A solution contém pelo menos um projeto de testes unitários e um de testes de integração. |
| CA-N06.2 | `dotnet test` na raiz da solution executa todos os testes e termina sem falhas. |
| CA-N06.3 | Os testes unitários e de integração não chamam a OpenAI real. Usam um cliente de IA simulado e rodam sem `OPENAI_API_KEY`. |
| CA-N06.4 | Os testes de integração cobrem: sucesso (200), cada regra de validação (400), resposta inválida da IA (502), timeout da IA (504) e Health Check (200 e 503). |
| CA-N06.5 | A cobertura de linhas da camada de aplicação/serviços é de pelo menos 80%. |
| CA-N06.6 | Os critérios que dependem da qualidade da IA (CA-03.2, CA-05.3, CA-06.3) ficam em uma suíte separada, executada manualmente ou sob demanda com uma chave real. |

### RNF-07 — Publicação no Azure App Service

| ID | Critério de aceite |
|----|--------------------|
| CA-N07.1 | A aplicação é publicada em um Azure App Service com runtime .NET 10. |
| CA-N07.2 | Após a publicação, `GET https://<app>.azurewebsites.net/health` retorna `200 OK`. |
| CA-N07.3 | Após a publicação, uma requisição válida a `POST /api/documentos/analise` retorna `200 OK` com o contrato de RF-08. |
| CA-N07.4 | As credenciais são configuradas como Application Settings do App Service (ou referências ao Key Vault), nunca no pacote publicado. |
| CA-N07.5 | O App Service aceita apenas HTTPS (`HTTPS Only` habilitado). |
| CA-N07.6 | O procedimento de publicação é reprodutível e está documentado (pipeline de CI/CD ou passo a passo). |

---

## 5. Premissas e pontos em aberto

Os itens abaixo foram assumidos para tornar os critérios verificáveis e precisam ser confirmados:

1. **Limites de tamanho:** 200 caracteres para `titulo` e 50.000 para `conteudo` (CA-02.3, CA-02.4). O limite de `conteudo` depende do modelo e do custo por requisição.
2. **Tempo limite da IA:** 60 segundos (CA-08.4).
3. **Rota e nomes dos campos:** em português (`/api/documentos/analise`, `tipoDocumento` etc.). Se o padrão corporativo for inglês, o contrato muda.
4. **Autenticação:** não há requisito de autenticação. Uma API corporativa exposta no App Service normalmente exige autenticação (API Key, Entra ID ou API Management). Recomenda-se definir isso antes da publicação.
5. **Lista de tipos de documento:** `tipoDocumento` é texto livre. Se for necessário um conjunto fechado (como em `nivelRisco`), ele deve ser definido.
6. **Dados sensíveis e LGPD:** o conteúdo enviado é transmitido à OpenAI. É preciso confirmar se isso é permitido pela política corporativa ou se deve ser usado o Azure OpenAI.
7. **Nome do projeto:** a solution se chama `DocumentoAI`, e o pedido original menciona "DocumentAI". Este documento adota `DocumentoAI`.
