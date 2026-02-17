# DevOps Portal (Backstage)

Portal interno baseado em Backstage para catalogo de servicos, scaffolder, TechDocs, busca e integracao com Kubernetes.

Este projeto roda em dois modos:
- `dev` (local): frontend em `:3000` e backend em `:7007` via `yarn start`
- `container/k8s`: backend empacotado em imagem Docker (porta `7007`)

## Stack e versoes

- Node.js: `22` ou `24` (obrigatorio, definido em `package.json`)
- Yarn: `4.4.1`
- TypeScript: `~5.8.0`
- Backstage CLI: `^0.35.2`
- PostgreSQL: `17` (recomendado `postgres:17-bookworm`)
- Docker: versao recente com BuildKit
- Kubernetes (opcional para deploy): `kubectl` + cluster (Kind, k3d, EKS, GKE, AKS etc.)

## Estrutura principal

- `app-config.yaml`: configuracao base local
- `app-config.production.yaml`: override para execucao em producao/container
- `packages/app`: frontend
- `packages/backend`: backend (plugins, API, catalog, scaffolder)
- `packages/backend/Dockerfile`: build da imagem do backend

## Pre-requisitos locais

Instale dependencias de compilacao nativa (necessarias para `isolated-vm` e outras libs):

```bash
sudo apt update
sudo apt install -y build-essential python3 make g++ pkg-config gcc-10 g++-10
```

Recomendado (WSL/Linux):

```bash
export CC=/usr/bin/gcc-10
export CXX=/usr/bin/g++-10
export PYTHON=/usr/bin/python3
```

## Banco de dados (PostgreSQL 17)

Suba o Postgres via Docker:

```bash
docker run -d \
  --name postgres17 \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=appdb \
  -p 5432:5432 \
  -v pgdata17:/var/lib/postgresql/data \
  postgres:17-bookworm
```

Validacao:

```bash
docker ps
docker logs -f postgres17
```

## Variaveis de ambiente

Arquivo `.env` esperado na raiz deste projeto (`devops-portal/.env`):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123
POSTGRES_DB=appdb
DATABASE_URL=postgresql://admin:admin123@localhost:5432/appdb
```

Exportar para sessao atual:

```bash
set -a
source .env
set +a
```

## Como iniciar local (fim a fim)

Na pasta `devops-portal`:

```bash
corepack enable
corepack prepare yarn@4.4.1 --activate
node -v
yarn -v
```

Instalacao limpa:

```bash
rm -rf node_modules .yarn/unplugged .yarn/build-state.yml .yarn/install-state.gz
yarn install
yarn tsc
```

Subir app + backend:

```bash
yarn start
```

Endpoints locais:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:7007`
- Healthcheck backend: `http://localhost:7007/healthcheck`

## WSL/Windows: acesso pelo navegador

Se o browser no Windows nao abrir `localhost:3000`, rode com bind em todas interfaces:

```bash
HOST=0.0.0.0 yarn start
```

Descubra o IP do WSL:

```bash
hostname -I | awk '{print $1}'
```

Acesse:

- `http://<WSL_IP>:3000`

Se necessario, ajuste `app-config.yaml`:

- `app.baseUrl`: `http://<WSL_IP>:3000`
- `backend.baseUrl`: `http://<WSL_IP>:7007`
- `backend.cors.origin`: `http://<WSL_IP>:3000`

## Erros comuns

### 1) `Cannot find module './out/isolated_vm'`

Causa: build nativo do `isolated-vm` falhou.

Checklist:

```bash
node -v   # deve ser 22 ou 24
which g++ && g++ --version
```

Reinstale com compilador novo:

```bash
export CC=/usr/bin/gcc-10
export CXX=/usr/bin/g++-10
rm -rf node_modules .yarn/unplugged .yarn/build-state.yml .yarn/install-state.gz
yarn install
node -e "require('isolated-vm'); console.log('isolated-vm OK')"
```

### 2) `EADDRINUSE` nas portas `3000`/`7007`

```bash
fuser -k 3000/tcp
fuser -k 7007/tcp
```

### 3) Warning `kubernetes config is missing`

Nao bloqueia o portal. Significa apenas que o plugin Kubernetes esta ativo sem cluster provider configurado.

## Build para container

Antes de gerar imagem:

```bash
yarn install --immutable
yarn tsc
yarn build:backend
```

Build da imagem:

```bash
yarn build-image
```

Imagem gerada: `backstage`

Teste local da imagem (exemplo):

```bash
docker run --rm -p 7007:7007 \
  --env-file .env \
  backstage
```

## Deploy em Kubernetes

Observacao: neste repositorio nao existe manifesto Helm/K8s dedicado para o Backstage. O fluxo abaixo eh o caminho padrao com `kubectl`.

### 1) Criar namespace

```bash
kubectl create namespace devops-portal
```

### 2) Criar secret com variaveis sensiveis

```bash
kubectl -n devops-portal create secret generic backstage-env \
  --from-literal=POSTGRES_HOST=postgres \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_USER=admin \
  --from-literal=POSTGRES_PASSWORD=admin123 \
  --from-literal=POSTGRES_DB=appdb
```

### 3) Aplicar deployment/service (exemplo)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backstage
  namespace: devops-portal
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backstage
  template:
    metadata:
      labels:
        app: backstage
    spec:
      containers:
        - name: backstage
          image: backstage:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 7007
          envFrom:
            - secretRef:
                name: backstage-env
---
apiVersion: v1
kind: Service
metadata:
  name: backstage
  namespace: devops-portal
spec:
  selector:
    app: backstage
  ports:
    - port: 80
      targetPort: 7007
      protocol: TCP
```

Aplicar:

```bash
kubectl apply -f k8s-backstage.yaml
kubectl -n devops-portal get pods,svc
```

### 4) Acessar

Port-forward rapido:

```bash
kubectl -n devops-portal port-forward svc/backstage 7007:80
```

Abrir:

- `http://localhost:7007`

## Fluxo recomendado de operacao

- Desenvolvimento local: `yarn start`
- Validacao de tipos: `yarn tsc`
- Build backend: `yarn build:backend`
- Build imagem: `yarn build-image`
- Deploy k8s: `kubectl apply -f ...`

## Comandos uteis

```bash
# status local de portas
ss -ltnp | rg ':3000|:7007'

# checar backend
curl -I http://localhost:7007/healthcheck

# logs do postgres
docker logs -f postgres17

# objetos no cluster
kubectl get pods -A
kubectl get svc -A
```

## Notas de seguranca

- Nao commitar `.env` com credenciais reais.
- Em producao, use Secret Manager (Vault, AWS Secrets Manager, GCP Secret Manager etc.).
- Troque `guest auth` por provider real (GitHub, OIDC, SAML etc.).
