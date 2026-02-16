# NGINX (Kubernetes)

Este diretório contém manifests básicos de `Namespace`, `Deployment` e `Service` para subir um NGINX no cluster.

## Arquivos

- `namespace.yaml`
  - Cria o namespace `nginx-app`.
  - Aplica labels de organização (`app: nginx`, `managed-by: argocd`).
- `deployment.yaml`
  - Cria o `Deployment` `nginx` no namespace `nginx-app`.
  - Usa imagem `nginx:1.25-alpine`.
  - `replicas: 2`.
  - Define `resources` (`requests`/`limits`).
  - Define `livenessProbe` e `readinessProbe` em `/` na porta `http`.
- `service.yaml`
  - Cria `Service` `ClusterIP` chamado `nginx`.
  - Expõe porta `80` e envia para `targetPort: http` do container.
  - Seleciona pods com label `app: nginx`.

## Como executar (kubectl)

Aplicar tudo:

```bash
kubectl apply -f apps/nginx/
```

Validar:

```bash
kubectl -n nginx-app get deploy,pods,svc
```

Acessar localmente (port-forward):

```bash
kubectl -n nginx-app port-forward svc/nginx 8080:80
```

Depois abra `http://localhost:8080`.

## Interação com Argo CD

Hoje este diretório não possui um `Application` próprio do Argo CD versionado aqui.
Você pode:

1. Aplicar manualmente com `kubectl` (comando acima), ou
2. Criar um `Application` apontando para `apps/nginx`.

Comandos úteis do Argo CD:

```bash
argocd app list
argocd app get <nome-do-app>
argocd app sync <nome-do-app>
argocd app logs <nome-do-app>
```

