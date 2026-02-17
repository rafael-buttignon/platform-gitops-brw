# nginx-web (Helm Chart)

Este diretório contém um chart Helm simples para subir um NGINX com configuração customizada via `ConfigMap`.

## Estrutura

- `Chart.yaml`
  - Metadados do chart (`name`, `version`, `appVersion`).
- `values.yaml`
  - Valores padrão do deploy (`replicaCount`, `image.tag`, `resources`, `namespace`, `serverBlock`).
- `templates/configmap.yaml`
  - Cria o `ConfigMap` `nginx-config` com o conteúdo de `serverBlock`.
- `templates/deployment.yaml`
  - Cria o `Deployment` `nginx-web`.
  - Monta `default.conf` em `/etc/nginx/conf.d/default.conf`.
- `templates/service.yaml`
  - Cria `Service` `ClusterIP` `nginx-web` na porta `80`.

## Como validar localmente (Helm)

```bash
cd /home/rafa/Dev/crossplane/lab-01
helm lint charts/nginx-web
helm template nginx-web charts/nginx-web
```

## Deploy direto com Helm

```bash
helm upgrade --install nginx-web charts/nginx-web \
  -n nginx-web \
  --create-namespace
```

Validar:

```bash
kubectl get all -n nginx-web
kubectl get configmap nginx-config -n nginx-web
```

Teste local:

```bash
kubectl port-forward svc/nginx-web 8080:80 -n nginx-web
curl -i http://localhost:8080/
curl -i http://localhost:8080/health
```

## Deploy via Argo CD (somente command line)

Criar ou atualizar a aplicação no Argo CD apontando para este chart:

```bash
argocd app create nginx-web \
  --repo https://github.com/rafael-buttignon/platform-gitops-brw.git \
  --path charts/nginx-web \
  --revision main \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace nginx-web \
  --sync-policy automated \
  --auto-prune \
  --self-heal \
  --sync-option CreateNamespace=true \
  --upsert
```

Sincronizar e validar:

```bash
argocd app sync nginx-web
argocd app get nginx-web
kubectl get all -n nginx-web
```

Teste local:

```bash
kubectl port-forward svc/nginx-web 8080:80 -n nginx-web
curl -i http://localhost:8080/
curl -i http://localhost:8080/health
```

## Remoção

Remover app do Argo CD:

```bash
argocd app delete nginx-web --cascade
```

Remover release Helm (se instalada via Helm):

```bash
helm uninstall nginx-web -n nginx-web
```
