API corporativa para **análise inteligente de documentos** com IA (OpenAI).

O cliente envia o título e o conteúdo textual de um documento e recebe uma análise em JSON estruturado: tipo do documento, resumo objetivo, palavras-chave, nível de risco e pontos de atenção.

> **Estado da implementação:** a estrutura da solution e esta documentação já estão publicadas. Os endpoints abaixo estão **especificados e em implementação**. Cada um aparece na lista de operações desta página, com o botão **Test Request**, assim que for entregue.

## Endpoints

| Método | Rota | Finalidade | Situação |
|--------|------|------------|----------|
| `POST` | `/api/documentos/analisar` | Analisa um documento com IA | em implementação |
| `GET` | `/health` | Informa se a aplicação está em execução e configurada | em implementação |

## Analisar documento

`POST /api/documentos/analisar` — `Content-Type: application/json`

### Requisição

| Campo | Tipo | Obrigatório | Regras |
|-------|------|-------------|--------|
| `titulo` | string | sim | Não pode ser vazio nem só espaços. Máximo de 200 caracteres. |
| `conteudo` | string | sim | Texto puro. Não pode ser vazio nem só espaços. Máximo de 50.000 caracteres. |

O corpo da requisição é limitado a 256 KB.

```json
{
  "titulo": "Contrato de prestação de serviços de suporte de TI",
  "conteudo": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\n\nCLÁUSULA 8ª – DA RESCISÃO\nEm caso de rescisão antecipada, será devida multa de 50% do valor remanescente..."
}
```

### Resposta `200 OK`

| Campo | Tipo | Regras |
|-------|------|--------|
| `tipoDocumento` | string | Ex.: `Contrato`, `Nota fiscal`. `Indeterminado` quando não há tipo reconhecível. |
| `resumo` | string | Objetivo, no idioma do documento, com no máximo 1.000 caracteres. |
| `nivelRisco` | string | `BAIXO`, `MEDIO` ou `ALTO`. |
| `palavrasChave` | string[] | De 1 a 10 itens, sem repetição. |
| `pontosAtencao` | string[] | Nunca nulo. Pelo menos 1 item quando o risco é `MEDIO` ou `ALTO`. |

```json
{
  "tipoDocumento": "Contrato",
  "resumo": "Contrato de suporte técnico de TI por 12 meses, com renovação automática e multa rescisória de 50%.",
  "nivelRisco": "MEDIO",
  "palavrasChave": ["prestação de serviços", "suporte de TI", "multa rescisória"],
  "pontosAtencao": [
    "Multa rescisória elevada: 50% do valor remanescente do contrato.",
    "Renovação automática sem prazo definido para manifestação contrária."
  ]
}
```

## Health Check

`GET /health` — não chama a IA e não consome tokens.

| Status | Corpo |
|--------|-------|
| `200 OK` | `{ "status": "Healthy" }` |
| `503 Service Unavailable` | `{ "status": "Unhealthy" }` (por exemplo, sem a chave da OpenAI configurada) |

## Códigos de resposta

| Status | Situação |
|--------|----------|
| `200` | Análise concluída. |
| `400` | Dados inválidos: campo ausente, vazio, acima do limite ou JSON malformado. |
| `404` | Rota inexistente. |
| `405` | Método não permitido na rota (cabeçalho `Allow` indica os métodos aceitos). |
| `413` | Corpo da requisição maior que 256 KB. |
| `415` | `Content-Type` diferente de `application/json`. |
| `500` | Erro interno inesperado. |
| `502` | O serviço de IA falhou ou devolveu uma resposta inválida. |
| `503` | O serviço de IA não está configurado. |
| `504` | O serviço de IA excedeu o tempo limite (60 segundos). |

## Formato de erro

Todas as respostas de erro seguem o padrão **Problem Details** (RFC 9457), com `Content-Type: application/problem+json`. Informe o `traceId` ao suporte para localizar a requisição nos logs.

```json
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
  "title": "Um ou mais campos são inválidos.",
  "status": 400,
  "instance": "POST /api/documentos/analisar",
  "traceId": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
  "errors": {
    "titulo": ["O título é obrigatório."],
    "conteudo": ["O conteúdo é obrigatório."]
  }
}
```

## Como testar por esta página

1. Escolha a operação na lista lateral.
2. Clique em **Test Request**, preencha o corpo com o exemplo acima e envie.
3. Veja o status, os cabeçalhos e o corpo da resposta no painel à direita.
4. Use o seletor de cliente para copiar a mesma chamada em cURL, C#, JavaScript e outras linguagens.

As requisições são enviadas para a mesma origem desta página. Portanto, a documentação funciona igual em desenvolvimento (`https://localhost:7041/scalar`) e em produção (`https://<app>.azurewebsites.net/scalar`).

## Segurança e privacidade

- Não envie documentos com dados pessoais ou sigilosos reais em testes: o conteúdo é processado pelo serviço de IA.
- O conteúdo dos documentos não é registrado nos logs da aplicação.
- Nenhuma credencial é exigida nesta versão. A forma de autenticação dos clientes ainda será definida.
