# Airflow (Argo CD + Helm Chart Oficial)

Este diretório contém a definição GitOps para subir o Airflow no cluster usando Argo CD e o chart oficial da Apache.

## Arquivos

- `namespace.yaml`
  - Cria o namespace `airflow`.
  - Labels de organização (`app: airflow`, `managed-by: argocd`).
- `application.yaml`
  - Recurso `argoproj.io/v1alpha1` do tipo `Application`.
  - `destination.server`: `https://kubernetes.default.svc` (cluster local/in-cluster).
  - `destination.namespace`: `airflow`.
  - `source.repoURL`: `https://airflow.apache.org`.
  - `source.chart`: `airflow`.
  - `syncPolicy.automated`: `prune` e `selfHeal` habilitados.
  - `syncOptions`: `CreateNamespace=true`, `ServerSideApply=true`.
  - Inclui `helm.values` inline com config básica de lab.
- `values.yaml`
  - Referência local das mesmas configurações usadas no `Application`.
  - Útil para leitura/manutenção de valores sem depender só do bloco inline.

## Principais configurações atuais

- `executor: LocalExecutor`
- `AIRFLOW__CORE__LOAD_EXAMPLES: "False"`
- Usuário inicial web:
  - `admin / admin` (somente laboratório)
- Banco:
  - `postgresql.enabled: true`
  - `postgresql.image.tag: latest`
- `redis.enabled: false`
- `ingress.web.enabled: false` (acesso por port-forward)
- Ajustes de estabilidade local:
  - `waitForMigrations.enabled: false` em `scheduler`, `triggerer`, `apiServer`, `dagProcessor`
  - `apiServer.args` roda:
    - `airflow db migrate`
    - `airflow fab-db migrate`
    - `airflow api-server --workers 1`

## Como executar

Aplicar namespace e app:

```bash
kubectl apply -f apps/airflow/namespace.yaml
kubectl apply -f apps/airflow/application.yaml
```

Ver status no Argo CD:

```bash
kubectl -n argocd get application airflow
```

Ver recursos do Airflow:

```bash
kubectl -n airflow get pods,svc
```

Acessar UI localmente:

```bash
kubectl -n airflow port-forward svc/airflow-api-server 8888:8080
```

Depois abra `http://localhost:8888`.

## Interagir com Argo CD

### Via kubectl (CRD Application)

```bash
kubectl -n argocd get applications
kubectl -n argocd describe application airflow
kubectl -n argocd annotate application airflow argocd.argoproj.io/refresh=hard --overwrite
```

### Via CLI do Argo CD

```bash
argocd app list
argocd app get airflow
argocd app sync airflow
argocd app wait airflow
```

## Observações

- Esta configuração é para laboratório/local.
- Para produção:
  - não usar `admin/admin`;
  - mover segredos para `Secret`/External Secret;
  - fixar versões de imagem/chart (evitar `latest` e `targetRevision: "*"`);
  - revisar recursos, probes e política de armazenamento.

