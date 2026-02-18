# API CEP

Microservico em FastAPI para consulta de CEP via ViaCEP.

## Visao geral

Esta API fornece endpoints de status e um endpoint de consulta de CEP:

- `GET /` para status basico do servico
- `GET /health` para healthcheck
- `GET /cep/{cep}` para consultar dados de endereco

## Base URL

Em execucao local com Docker:

```bash
http://localhost:8081
```

## Endpoints

### `GET /`

Retorna estado basico da aplicacao.

Resposta `200`:

```json
{
  "service": "api-cep",
  "status": "ok"
}
```

### `GET /health`

Retorna healthcheck simples da API.

Resposta `200`:

```json
{
  "status": "healthy"
}
```

### `GET /cep/{cep}`

Consulta um CEP brasileiro no ViaCEP.

Regras de validacao:

- Aceita CEP com 8 digitos
- Aceita com ou sem hifen (ex.: `01001000` ou `01001-000`)

Exemplo de requisicao:

```bash
curl http://localhost:8081/cep/01001000
```

Exemplo de resposta `200`:

```json
{
  "cep": "01001-000",
  "logradouro": "Praca da Se",
  "complemento": "lado impar",
  "bairro": "Se",
  "localidade": "Sao Paulo",
  "uf": "SP",
  "ibge": "3550308",
  "gia": "1004",
  "ddd": "11",
  "siafi": "7107"
}
```

## Codigos de resposta

- `200`: Sucesso
- `400`: CEP invalido
- `404`: CEP nao encontrado
- `502`: Falha de rede/erro no servico ViaCEP
- `504`: Timeout ao consultar ViaCEP

Exemplo de erro:

```json
{
  "detail": "CEP invalido"
}
```

## Dependencia externa

A API depende do servico `https://viacep.com.br`.
Sem conectividade externa, o endpoint `GET /cep/{cep}` pode retornar `502` ou `504`.

## Execucao local rapida

```bash
docker build -t api-cep:latest .
docker run -d --name cep-api -p 8081:8000 api-cep:latest
```

Testes:

```bash
curl http://localhost:8081/
curl http://localhost:8081/health
curl http://localhost:8081/cep/01001000
```
