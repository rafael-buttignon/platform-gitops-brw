# API CEP

Microservico em FastAPI para consulta de CEP usando ViaCEP.

## O que esta API faz

- Exponibiliza endpoint de consulta `GET /cep/{cep}`
- Valida formato do CEP (8 digitos)
- Consulta o servico externo ViaCEP
- Retorna erros padronizados para timeout, CEP invalido e CEP nao encontrado

## Stack

- Python `3.11` (imagem base: `python:3.11-slim`)
- FastAPI
- Uvicorn
- HTTPX
- Docker

## Estrutura

- `main.py`: aplicacao FastAPI e endpoints
- `requirements.txt`: dependencias Python
- `Dockerfile`: build da imagem

## Endpoints

- `GET /`
  - status basico do servico
  - resposta exemplo: `{"service":"api-cep","status":"ok"}`

- `GET /health`
  - healthcheck
  - resposta exemplo: `{"status":"healthy"}`

- `GET /cep/{cep}`
  - consulta CEP no ViaCEP
  - exemplo: `GET /cep/01001000`

## Codigos de resposta

- `200`: sucesso
- `400`: CEP invalido
- `404`: CEP nao encontrado
- `502`: falha de rede/servico externo
- `504`: timeout ao consultar ViaCEP

## Como rodar com Docker (recomendado)

### 1) Build da imagem

```bash
cd /home/rafa/Dev/crossplane/lab-01/api/cep
docker build -t api-cep:latest .
```

### 2) Subir container

Porta da API no container: `8000`.

Mapeamento recomendado no host: `8081`.

```bash
docker rm -f cep-api 2>/dev/null || true
docker run -d --name cep-api -p 8081:8000 api-cep:latest
```

### 3) Testar

```bash
curl http://localhost:8081/
curl http://localhost:8081/health
curl http://localhost:8081/cep/01001000
```

Docs interativa:

- `http://localhost:8081/docs`

## Comandos uteis Docker

```bash
# containers rodando
docker ps

# ver logs da API
docker logs -f cep-api

# parar/remover container
docker rm -f cep-api

# listar imagens
docker images | grep api-cep
```

## Troubleshooting

### 1) `port is already allocated`

A porta no host ja esta em uso.

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}" | grep 8081
docker rm -f <container_que_esta_usando_a_porta>
```

Ou rode em outra porta:

```bash
docker run -d --name cep-api -p 8082:8000 api-cep:latest
```

### 2) `container name already in use`

Ja existe container com o mesmo nome (`cep-api`).

```bash
docker rm -f cep-api
```

### 3) `Connection reset by peer`

Pode acontecer logo apos subir o container, antes da app ficar pronta.

```bash
docker logs -f cep-api
curl --max-time 10 http://localhost:8081/health
```

### 4) `curl` fica travado

Nao use `Ctrl+Z` durante o teste, isso suspende o processo.

```bash
jobs
kill %1 %2 2>/dev/null || true
```

## Rodar sem Docker (opcional)

```bash
cd /home/rafa/Dev/crossplane/lab-01/api/cep
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Testes locais:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/cep/01001000
```

## Exemplo Kubernetes (opcional)

Arquivo `k8s-api-cep.yaml` (exemplo minimo):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-cep
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api-cep
  template:
    metadata:
      labels:
        app: api-cep
    spec:
      containers:
        - name: api-cep
          image: api-cep:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: api-cep
spec:
  selector:
    app: api-cep
  ports:
    - port: 80
      targetPort: 8000
```

Aplicar:

```bash
kubectl apply -f k8s-api-cep.yaml
kubectl get pods,svc
kubectl port-forward svc/api-cep 8081:80
```

Acesso:

- `http://localhost:8081/health`

## Observacoes

- Esta API depende do ViaCEP; sem acesso externo a internet, `GET /cep/{cep}` pode retornar `502`/`504`.
- Para producao, adicione rate limit, retries e observabilidade (logs estruturados/metricas).
