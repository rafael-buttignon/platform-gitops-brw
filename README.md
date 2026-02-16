# Lab 01 - Crossplane + Argo CD + Apps (Local)

Este repositório organiza um laboratório local com Kubernetes (Kind), Argo CD e aplicações (Airflow/Nginx), seguindo um fluxo GitOps.

## Inventario tecnico (versoes)

### Ferramentas locais (CLI)

| Ferramenta | Versao observada |
|---|---|
| `kind` | `0.32.0-alpha+9145d421e0d4f7` |
| `kubectl` | `v1.32.2` |
| `kustomize` (embutido no kubectl) | `v5.5.0` |
| `helm` | `v3.20.0+gb2e4314` |
| `argocd` CLI | `v3.3.0+fd6b7d5` |

### Runtime Kubernetes local

| Componente | Versao observada |
|---|---|
| Kubernetes node (`kind`) | `v1.27.3` |
| Container runtime | `containerd://1.7.1` |

### Pacotes/charts/providers usados no repo

| Item | Versao/Tag | Onde esta definido |
|---|---|---|
| Argo CD (imagem principal) | `quay.io/argoproj/argocd:v3.3.0` | cluster (`argocd` namespace) |
| Argo CD Dex | `ghcr.io/dexidp/dex:v2.43.0` | cluster (`argocd` namespace) |
| Argo CD Redis | `public.ecr.aws/docker/library/redis:8.2.3-alpine` | cluster (`argocd` namespace) |
| Airflow Helm Chart | `1.18.0` | `apps/airflow/application.yaml` |
| Airflow image | `apache/airflow:3.0.2` (default do chart em execucao atual) | cluster (`airflow` namespace) |
| PostgreSQL do Airflow | `docker.io/bitnami/postgresql:latest` | `apps/airflow/values.yaml` |
| Nginx | `nginx:1.25-alpine` | `apps/nginx/deployment.yaml` |
| Provider Family Azure (Crossplane) | `xpkg.upbound.io/upbound/provider-family-azure:v1.10.0` | `platform-bootstrap/provider-azure.yaml` |
| Provider Azure Storage (Crossplane) | `xpkg.upbound.io/upbound/provider-azure-storage:v1.10.0` | `platform-bootstrap/provider-azure-storage.yaml` |

### Bibliotecas/CRDs relevantes

| Tipo | Detalhe |
|---|---|
| Argo CD Application CRD | `argoproj.io/v1alpha1`, `kind: Application` |
| Crossplane Composition/XRD | `apiextensions.crossplane.io/v1` |
| Azure managed resources (Upbound) | `azure.upbound.io/v1beta1`, `storage.azure.upbound.io/v1beta2` |

## Estrutura atual

- `apps/`
  - `apps/airflow/`
    - `application.yaml`: Argo CD Application do Airflow (chart oficial + values do Git)
    - `values.yaml`: valores do chart Airflow
    - `namespace.yaml`: namespace `airflow`
    - `README.md`: documentação específica do Airflow
  - `apps/nginx/`
    - `namespace.yaml`, `deployment.yaml`, `service.yaml`
    - `README.md`: documentação específica do Nginx
- `platform-bootstrap/`
  - YAMLs de bootstrap/infra (Crossplane + recursos Azure) movidos da raiz
  - `platform-bootstrap/README.md`: documentação antiga detalhada do laboratório
- `scripts/`
  - scripts auxiliares locais

## Sobre Argo CD (conceito)

Sim: Argo CD é, na prática, um reconciliador GitOps.

- Estado desejado: o que está no Git
- Estado real: o que está no cluster
- Ação do Argo CD: compara e sincroniza continuamente (self-heal/prune quando configurado)

No Airflow, o `Application` usa `sources` (multi-source):

1. source do chart oficial (`https://airflow.apache.org`)
2. source do seu repositório GitHub para carregar `apps/airflow/values.yaml`

## Fluxo diário (ligar o computador)

1. Subir Docker/daemon
2. Validar contexto/cluster:

```bash
kubectl cluster-info
kubectl get nodes
```

3. Validar Argo CD e apps:

```bash
kubectl -n argocd get pods
kubectl -n argocd get applications
kubectl -n airflow get pods
kubectl -n nginx-app get pods
```

4. Reabrir port-forwards (sempre necessário após reboot):

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443
kubectl -n airflow port-forward svc/airflow-api-server 8888:8080
kubectl -n nginx-app port-forward svc/nginx 8081:80
```

## Se o ambiente foi perdido/resetado

Cenário: cluster Kind sumiu, foi recriado, ou você resetou a máquina.

Passo a passo recomendado:

1. Recriar/ligar cluster Kubernetes local (Kind)
2. Reinstalar Argo CD no cluster
3. Aplicar o `Application` do Airflow e manifests necessários:

```bash
kubectl apply -f apps/airflow/namespace.yaml
kubectl apply -f apps/airflow/application.yaml
kubectl apply -f apps/nginx/
```

4. Validar sincronização:

```bash
kubectl -n argocd get application airflow
kubectl -n airflow get pods,svc
kubectl -n nginx-app get deploy,pods,svc
```

5. Reabrir port-forward para acesso local (UI)

## Necessidades importantes para não travar

- Git remoto acessível (Argo precisa ler o repo)
- `apps/airflow/application.yaml` com `repoURL` e `targetRevision` corretos
- credenciais/sensíveis fora do Git (ex.: `azure-credentials.json` apenas local)
- evitar `latest` e `*` em produção; para lab pode funcionar
- se houver erro no Airflow web, verificar logs do `api-server` primeiro

## Comandos de diagnóstico rápido

```bash
kubectl -n argocd get application airflow -o wide
kubectl -n airflow get pods -o wide
kubectl -n airflow logs deploy/airflow-api-server --tail=200
kubectl -n nginx-app get all
```

## Notas

- Este repositório é voltado para laboratório local.
- Para hardening/produção: secrets dedicados, pin de versões, RBAC, observabilidade, backups e política de recuperação.
- Evite credenciais no Git; mantenha arquivos sensíveis apenas localmente.

## Referencias

- Repositorio de referencia informado: `https://github.com/iesodias/engenharia-plataforma/tree/main`
- Argo CD: `https://argo-cd.readthedocs.io/`
- Apache Airflow Helm Chart: `https://airflow.apache.org/docs/helm-chart/stable/index.html`
- Kind: `https://kind.sigs.k8s.io/`
