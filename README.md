# Crossplane Lab 01 — Guia Completo

## Índice

1. [O que é Crossplane?](#o-que-é-crossplane)
2. [Arquitetura e Comunicação](#arquitetura-e-comunicação)
3. [Kind vs kubectl](#kind-vs-kubectl)
4. [Crossplane vs Terraform](#crossplane-vs-terraform)
5. [Kind (local) vs Kubernetes na Nuvem](#kind-local-vs-kubernetes-na-nuvem)
6. [Service Principal](#service-principal)
7. [XRD, Composition e Claim](#xrd-composition-e-claim)
8. [Pipeline Mode](#pipeline-mode)
9. [Fluxo de Desenvolvimento Local (Testes)](#fluxo-de-desenvolvimento-local-testes)
10. [Fluxo de Produção (Como as empresas fazem)](#fluxo-de-produção-como-as-empresas-fazem)
11. [Autenticação em Produção vs Local](#autenticação-em-produção-vs-local)
12. [Onde encontrar Providers e Documentação](#onde-encontrar-providers-e-documentação)
13. [Passo a Passo do que fizemos](#passo-a-passo-do-que-fizemos)
14. [Comandos úteis de referência](#comandos-úteis-de-referência)
15. [Troubleshooting — Problemas comuns](#troubleshooting--problemas-comuns)

---

## O que é Crossplane?

O Crossplane é uma ferramenta **open-source** que roda **dentro do Kubernetes** como um controller. Ele permite que você crie e gerencie recursos de infraestrutura em nuvem (Azure, AWS, GCP) usando **manifestos YAML do Kubernetes**.

Em vez de ir ao portal da Azure ou usar o `az cli` para criar um Resource Group, você escreve um YAML e aplica com `kubectl apply`. O Crossplane cuida do resto.

---

## Arquitetura e Comunicação

### Cadeia de dependência

```
Docker → Kind → Cluster Kubernetes → Crossplane → Providers → Azure/AWS/GCP
```

### Fluxo de comunicação detalhado

```
┌──────────────────────────────────────────────────────────────────────┐
│  SUA MÁQUINA LOCAL                                                   │
│                                                                      │
│  1. Você escreve:   resource-group.yaml                              │
│  2. Você executa:   kubectl apply -f resource-group.yaml             │
│                          │                                           │
│                          ▼                                           │
│  ┌───────────────────────────────────────────────────────────┐       │
│  │  CLUSTER KUBERNETES (Kind / AKS / EKS / GKE)             │       │
│  │                                                           │       │
│  │  ┌─────────────────────────────────────────────────┐     │       │
│  │  │  API Server (kube-apiserver)                     │     │       │
│  │  │  • Recebe o YAML                                 │     │       │
│  │  │  • Valida contra os CRDs registrados             │     │       │
│  │  │  • Salva no etcd (banco de dados do cluster)     │     │       │
│  │  └──────────────────┬──────────────────────────────┘     │       │
│  │                     │                                     │       │
│  │                     ▼                                     │       │
│  │  ┌─────────────────────────────────────────────────┐     │       │
│  │  │  CROSSPLANE (pod no namespace crossplane-system) │     │       │
│  │  │  • Detecta o novo recurso ResourceGroup          │     │       │
│  │  │  • Lê as credenciais do Secret (azure-secret)    │     │       │
│  │  │  • Lê o ProviderConfig (default)                 │     │       │
│  │  └──────────────────┬──────────────────────────────┘     │       │
│  │                     │                                     │       │
│  └─────────────────────┼─────────────────────────────────────┘       │
│                        │                                             │
└────────────────────────┼─────────────────────────────────────────────┘
                         │  HTTPS (API REST da Azure)
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  MICROSOFT AZURE                                               │
│                                                                │
│  • Azure Resource Manager (ARM) recebe a requisição            │
│  • Autentica via clientId + clientSecret (Service Principal)   │
│  • Cria o Resource Group "rg-crossplane-lab01" em "eastus"     │
│  • Retorna status 200 OK                                       │
│                                                                │
│  ← Crossplane atualiza o status no Kubernetes:                 │
│     READY: True, SYNCED: True                                  │
└────────────────────────────────────────────────────────────────┘
```

### O que cada componente faz

| Componente | Função |
|---|---|
| **Docker** | Motor de containers. O Kind usa containers Docker como "nós" do cluster |
| **Kind** | Cria um cluster Kubernetes local usando Docker (Kubernetes IN Docker) |
| **Kubernetes** | Orquestrador. Fornece API, RBAC, reconciliação, HA para o Crossplane |
| **Helm** | Gerenciador de pacotes. Usado para instalar o Crossplane no cluster |
| **Crossplane** | Controller que converte recursos YAML em chamadas de API para nuvens |
| **Provider** | Plugin do Crossplane que sabe se comunicar com uma nuvem específica |
| **ProviderConfig** | Configuração que diz ao Provider quais credenciais usar |
| **CRDs** | Custom Resource Definitions — registram novos tipos de recursos no Kubernetes |
| **Service Principal** | Identidade criada no Azure AD para autenticação programática |

### Modelo de reconciliação

O Crossplane usa o **modelo de reconciliação** do Kubernetes:

1. Você declara o **estado desejado** (ex: "quero um Resource Group chamado rg-crossplane-lab01 em eastus")
2. O Crossplane **compara** o estado desejado com o estado real na Azure
3. Se não existe → **cria**
4. Se existe mas está diferente → **atualiza**
5. Se você deleta o YAML → **deleta na Azure**
6. Esse ciclo roda **continuamente** (a cada poucos segundos)

---

## Kind vs kubectl

São ferramentas **complementares**, não dependentes:

| | **kubectl** | **kind** |
|---|---|---|
| **O que é** | CLI para gerenciar **recursos** dentro de um cluster | CLI para gerenciar o **cluster** em si |
| **Função** | Criar pods, deployments, aplicar YAMLs | Criar e destruir clusters Kubernetes locais |
| **Analogia** | O **gerenciador de arquivos** do sistema | O **instalador** do sistema operacional |
| **Exemplo** | `kubectl apply -f resource-group.yaml` | `kind create cluster --name crossplane-lab` |
| **Depende de** | Um cluster já existir | Docker |

```
kind  → cria/destroi o cluster (a "máquina")
kubectl → gerencia o que roda dentro do cluster (os "programas")
```

- `kubectl` **não** pode criar clusters
- `kind` **não** pode criar pods/deployments
- `kubectl` funciona com **qualquer** cluster (Kind, AKS, EKS, GKE, Minikube, etc.)
- Você usa `kind` **uma vez** para criar o cluster, depois usa `kubectl` **o tempo todo**

---

## Crossplane vs Terraform

| Aspecto | Crossplane | Terraform |
|---|---|---|
| **Formato** | YAML (manifestos Kubernetes) | HCL (`.tf`) |
| **Onde roda** | Dentro do Kubernetes (como pod) | Na sua máquina local ou CI/CD |
| **Estado** | Armazenado no etcd do Kubernetes | Arquivo `terraform.tfstate` (local ou remoto) |
| **Reconciliação** | Contínua e automática | Sob demanda (`terraform apply`) |
| **Drift detection** | Automática (detecta e corrige mudanças manuais) | Manual (`terraform plan`) |
| **Linguagem** | YAML declarativo | HCL declarativo + funções |
| **Dependência** | Precisa de um cluster Kubernetes rodando | Só precisa do binário `terraform` |
| **Nomenclatura** | `kind: ResourceGroup` | `azurerm_resource_group` |
| **Validação** | `kubectl apply --dry-run=client` | `terraform validate` / `terraform plan` |
| **Providers** | CRDs no cluster + docs Upbound | Registry (`registry.terraform.io`) |
| **Curva de aprendizado** | Precisa saber Kubernetes | Independente de Kubernetes |

### Quando usar cada um?

- **Crossplane**: quando você já tem Kubernetes e quer gerenciar infra como recursos nativos do cluster, com reconciliação contínua
- **Terraform**: quando você quer algo standalone, sem depender de Kubernetes, ou para automação em CI/CD pipelines

---

## Kind (local) vs Kubernetes na Nuvem

### O que muda?

**Quase nada nos YAMLs.** Os manifestos do Crossplane são **idênticos** independente de onde o cluster roda.

| Aspecto | Kind (local) | AKS / EKS / GKE (nuvem) |
|---|---|---|
| **Criação do cluster** | `kind create cluster` | `az aks create` / Console / Terraform |
| **Onde roda** | Containers Docker no seu PC | VMs na nuvem |
| **Performance** | Limitada (recursos do PC) | Escalável (VMs dedicadas) |
| **Disponibilidade** | Desliga com o PC | 24/7 |
| **Custo** | Grátis | Pago |
| **YAMLs do Crossplane** | **Idênticos** | **Idênticos** |
| **Comandos kubectl** | **Idênticos** | **Idênticos** |
| **Autenticação** | kubeconfig local | kubeconfig da nuvem |
| **Uso recomendado** | Dev / Lab / Testes | Staging / Produção |

### Como seria no AKS (Azure)?

```bash
# Em vez de "kind create cluster", você faria:
az aks create \
  --resource-group meu-rg \
  --name meu-aks \
  --node-count 2 \
  --generate-ssh-keys

# Baixar o kubeconfig
az aks get-credentials --resource-group meu-rg --name meu-aks

# A partir daqui, TUDO é igual:
helm install crossplane crossplane-stable/crossplane ...
kubectl apply -f provider-azure.yaml
kubectl apply -f provider-config-azure.yaml
kubectl apply -f resource-group.yaml
```

### Vantagens de rodar na nuvem

- Cluster sempre ligado → reconciliação 24/7
- Mais memória/CPU para o Crossplane processar muitos recursos
- Integração com **Managed Identity** (sem precisar de clientSecret)
- Alta disponibilidade com múltiplos nós

### Vantagem do Kind (local)

- Perfeito para **aprender e testar** sem custo
- Rápido de criar e destruir
- Não precisa de internet para o cluster em si (só para o Crossplane falar com a Azure)

---

## Service Principal

Um **Service Principal** é uma "conta de serviço" no Azure AD — um **usuário robô** para que aplicações (como o Crossplane) se autentiquem na Azure programaticamente.

### Composição

```
Service Principal
├── appId (clientId)        → "login" do robô
├── password (clientSecret) → "senha" do robô
├── tenant (tenantId)       → qual Azure AD ele pertence
└── Role Assignment         → o que ele pode fazer (ex: Contributor)
```

### Por que não usar sua conta pessoal?

| Sua conta | Service Principal |
|---|---|
| Tem MFA, login interativo | Autenticação via API (sem interação) |
| Se você mudar a senha, quebra tudo | Credencial independente da sua |
| Tem acesso a tudo | Pode ter permissões limitadas (princípio do menor privilégio) |
| Não dá pra usar em automação | Feito para automação |

### No contexto do nosso lab

```
Crossplane precisa criar recursos na Azure
    → precisa se autenticar
    → usa o Service Principal "crossplane-labs-sp"
    → que tem role "Contributor" na subscription
    → as credenciais estão no Secret "azure-secret" no Kubernetes
```

---

## XRD, Composition e Claim

O Crossplane permite criar **APIs customizadas** usando 3 peças que se conectam:

### Analogia

| Arquivo | Analogia | Função |
|---|---|---|
| **XRD** | O **cardápio** | Define o que pode ser pedido e quais opções existem |
| **Composition** | A **receita do chef** | Diz como preparar o prato (quais recursos Azure criar) |
| **Claim** | O **pedido do cliente** | O dev faz o pedido com as configs desejadas |

### Quem cria o quê

| Persona | Cria | Conhecimento necessário |
|---|---|---|
| **Time de Plataforma** | XRD + Composition | Azure, Crossplane, infra |
| **Dev / Usuário** | Claim | Só os parâmetros simples |

### Como os 3 arquivos se conectam

```
XRD (xrd-storagebucket.yaml)
│
│  Define:
│    group: custom.crossplane.io
│    kind: XStorageBucket              ──────┐
│    claimNames.kind: StorageBucket    ───┐  │
│    version: v1alpha1                 ─┐ │  │
│    parameters: environment,          │ │  │
│      location, storageClass, etc.    │ │  │
│                                      │ │  │
├──────────────────────────────────────┘ │  │
│                                        │  │
▼                                        │  │
Composition (composition-storagebucket.yaml)│
│                                        │  │
│  Referencia o XRD via:                 │  │
│    compositeTypeRef:                   │  │
│      apiVersion: custom.crossplane.io/v1alpha1  ← group + version
│      kind: XStorageBucket              ←────────┘
│                                        │
│  Mapeia parameters → recursos Azure    │
│  via patches (fromFieldPath → toFieldPath)
│                                        │
│  metadata.name: storagebucket-azure ─┐ │
│                                      │ │
├──────────────────────────────────────┘ │
│                                        │
▼                                        │
Claim (claim-storagebucket.yaml)         │
                                         │
  Referencia o XRD via:                  │
    apiVersion: custom.crossplane.io/v1alpha1  ← group + version
    kind: StorageBucket                  ←───┘

  Referencia a Composition via:
    compositionRef:
      name: storagebucket-azure          ← metadata.name da Composition

  Preenche os parameters definidos no XRD:
    environment: dev
    location: eastus
    storageClass: standard
```

### Sem Claim vs Com Claim

**Sem Claim** (o dev precisa saber tudo da Azure):
```yaml
apiVersion: storage.azure.upbound.io/v1beta2
kind: Account
spec:
  forProvider:
    accountKind: StorageV2
    accountTier: Standard
    accountReplicationType: LRS
    location: eastus
    resourceGroupName: "rg-crossplane-lab01"
  providerConfigRef:
    name: default
```

**Com Claim** (o dev só preenche o essencial):
```yaml
apiVersion: custom.crossplane.io/v1alpha1
kind: StorageBucket
metadata:
  name: brewdat
spec:
  parameters:
    environment: dev
    location: eastus
    storageClass: standard
```

---

## Pipeline Mode

A Composition pode usar **dois modos**:

| Modo | Status | Descrição |
|---|---|---|
| `resources` (legado) | Deprecated | Recursos e patches direto no spec |
| `Pipeline` (moderno) | **Recomendado** | Usa Functions para processar recursos |

### O que é o Pipeline Mode?

```yaml
spec:
  mode: Pipeline
  pipeline:
    - step: patch-and-transform
      functionRef:
        name: function-patch-and-transform    # ← Function instalada no cluster
      input:
        apiVersion: pt.fn.crossplane.io/v1beta1
        kind: Resources
        resources:
          - name: meu-recurso
            base: ...
            patches: ...
```

### Function patch-and-transform

É uma **Function** que precisa ser instalada no cluster antes de usar Pipeline mode:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1beta1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.upbound.io/crossplane-contrib/function-patch-and-transform:v0.7.0
EOF
```

Verificar se está rodando:
```bash
kubectl get functions
```

### Vantagens do Pipeline

- Múltiplos recursos na mesma Composition (ex: Resource Group + Storage Account)
- Transforms avançados (`Format`, `Replace`, `Map`, `Convert`)
- Encadeamento de steps
- Extensível com Functions customizadas

### Transforms úteis

```yaml
# Formatar string: "my-bucket" → "rg-my-bucket"
transforms:
  - type: string
    string:
      type: Format
      fmt: "rg-%s"

# Substituir caracteres: "my-bucket" → "mybucket"
transforms:
  - type: string
    string:
      type: Replace
      replace:
        search: "-"
        replace: ""

# Mapear valores: "standard" → "Standard"
transforms:
  - type: map
    map:
      standard: Standard
      premium: Premium
```

### Cuidados

- **Nomes de Storage Account**: máximo 24 caracteres, só letras minúsculas e números, sem hífens
- **Sufixo aleatório**: o Crossplane adiciona um sufixo ao nome do Claim (ex: `brewdat` → `brewdat-6st4v`), o que pode gerar nomes longos demais
- Use nomes curtos no Claim para evitar problemas

---

## Fluxo de Desenvolvimento Local (Testes)

Este é o fluxo que o dev usa no **dia a dia** para testar antes de subir para produção.

### Pré-requisitos no laptop do dev

```
Laptop do Dev
├── Docker Desktop (ou Docker Engine no Linux/WSL2)
├── Kind (para criar clusters locais)
├── kubectl (para gerenciar o cluster)
├── Helm (para instalar o Crossplane)
├── az cli (para login na Azure)
└── Git (para versionamento)
```

### Passo a passo do desenvolvimento local

```
┌──────────────────────────────────────────────────────────────────┐
│  LAPTOP DO DEV                                                    │
│                                                                    │
│  PASSO 1 — Preparar ambiente (uma vez)                             │
│  ══════════════════════════════════════                             │
│  $ kind create cluster --name crossplane-dev                       │
│  $ helm install crossplane crossplane-stable/crossplane \          │
│      --namespace crossplane-system --create-namespace --wait       │
│  $ kubectl apply -f provider-azure.yaml                            │
│  $ kubectl apply -f provider-azure-storage.yaml                    │
│  $ kubectl create secret generic azure-secret ...                  │
│  $ kubectl apply -f provider-config-azure.yaml                     │
│  $ kubectl apply -f xrd-storagebucket.yaml                         │
│  $ kubectl apply -f composition-storagebucket.yaml                 │
│                                                                    │
│  PASSO 2 — Desenvolver e testar                                    │
│  ═════════════════════════════                                     │
│  $ vim claim-storage-dev.yaml          ← escreve/edita o Claim     │
│  $ kubectl apply -f claim-storage-dev.yaml  ← testa localmente    │
│  $ kubectl get storagebucket -w        ← acompanha o status        │
│  $ az storage account list -o table    ← confirma na Azure sandbox │
│                                                                    │
│  PASSO 3 — Limpar (não gastar dinheiro)                            │
│  ══════════════════════════════════════                             │
│  $ kubectl delete -f claim-storage-dev.yaml  ← deleta na Azure    │
│  $ kind delete cluster --name crossplane-dev ← destroi o cluster   │
│                                                                    │
│  PASSO 4 — Subir para o Git                                        │
│  ══════════════════════════                                        │
│  $ git add claim-storage-dev.yaml                                  │
│  $ git commit -m "feat: adiciona storage account para app X"       │
│  $ git push origin feature/storage-app-x                           │
│  $ Abre PR no GitHub → Aguarda review                              │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Pontos importantes

- O dev usa uma **conta Azure sandbox/dev** (não a de produção)
- Os recursos **são criados de verdade na Azure** mesmo com Kind local
- Sempre **deletar os recursos** depois de testar para não gastar
- O Kind **só precisa estar rodando** enquanto testa (desliga com o PC)
- O setup do passo 1 pode ser automatizado com um script

---

## Fluxo de Produção (Como as empresas fazem)

### Visão geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────────┐    git push     ┌──────────┐    sync     ┌────────────┐  │
│  │          │ ──────────────► │          │ ──────────► │            │  │
│  │  DEV     │    PR/review    │  GITHUB  │   (GitOps)  │  AKS       │  │
│  │  (laptop)│ ◄────────────── │  (Git)   │             │  (nuvem)   │  │
│  │          │    feedback     │          │             │            │  │
│  └──────────┘                 └──────────┘             └─────┬──────┘  │
│                                                              │         │
│                                                     Crossplane         │
│                                                              │         │
│                                                              ▼         │
│                                                       ┌────────────┐   │
│                                                       │  AZURE     │   │
│                                                       │  Resources │   │
│                                                       └────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detalhamento completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SETUP INICIAL (feito UMA VEZ pelo time de plataforma)                  │
│                                                                         │
│  1. Criar o AKS na Azure                                                │
│     $ az aks create --resource-group rg-plataforma --name aks-prod      │
│                                                                         │
│  2. Instalar Crossplane no AKS                                          │
│     $ az aks get-credentials --name aks-prod --resource-group rg-plat.  │
│     $ helm install crossplane crossplane-stable/crossplane ...          │
│                                                                         │
│  3. Instalar Providers, Functions, XRDs, Compositions                   │
│     $ kubectl apply -f providers/                                       │
│     $ kubectl apply -f platform/                                        │
│                                                                         │
│  4. Instalar ArgoCD no AKS                                              │
│     $ helm install argocd argo/argo-cd ...                              │
│     → Configurar para monitorar o repositório Git                       │
│                                                                         │
│  5. Configurar autenticação (Workload Identity)                         │
│     → Sem senhas, sem secrets                                           │
│                                                                         │
│  6. Configurar RBAC                                                     │
│     → Devs: read-only em prod                                           │
│     → ArgoCD: full access para aplicar YAMLs                            │
│     → Plataforma: admin                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  DIA A DIA — Dev quer criar um Storage Account                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  DEV (laptop)                                                   │    │
│  │                                                                 │    │
│  │  1. Testa localmente (opcional)                                 │    │
│  │     $ kind create cluster                                       │    │
│  │     $ ... (setup local)                                         │    │
│  │     $ kubectl apply -f claim-storage.yaml (testa)               │    │
│  │     $ kubectl delete -f claim-storage.yaml (limpa)              │    │
│  │                                                                 │    │
│  │  2. Sobe para o Git                                             │    │
│  │     $ git checkout -b feature/novo-storage                      │    │
│  │     $ git add claims/prod/claim-storage-app-x.yaml              │    │
│  │     $ git commit -m "feat: storage account para app X"          │    │
│  │     $ git push origin feature/novo-storage                      │    │
│  │     → Abre Pull Request no GitHub                               │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  GITHUB (repositório)                                           │    │
│  │                                                                 │    │
│  │  3. Pull Request                                                │    │
│  │     → CI roda validações automáticas (lint, dry-run)            │    │
│  │     → Lead/SRE faz code review                                  │    │
│  │     → Aprovado ✅                                                │    │
│  │     → Merge na branch main                                      │    │
│  │                                                                 │    │
│  │  Estrutura do repositório:                                      │    │
│  │  infra-crossplane/                                              │    │
│  │  ├── providers/                                                 │    │
│  │  │   ├── provider-azure.yaml                                    │    │
│  │  │   ├── provider-azure-storage.yaml                            │    │
│  │  │   └── provider-config-azure.yaml                             │    │
│  │  ├── platform/                                                  │    │
│  │  │   ├── xrd-storagebucket.yaml                                 │    │
│  │  │   ├── composition-storagebucket.yaml                         │    │
│  │  │   └── function-patch-and-transform.yaml                      │    │
│  │  └── claims/                                                     │    │
│  │      ├── dev/                                                   │    │
│  │      │   └── claim-storage-dev.yaml                             │    │
│  │      ├── staging/                                                │    │
│  │      │   └── claim-storage-staging.yaml                         │    │
│  │      └── prod/                                                   │    │
│  │          └── claim-storage-app-x.yaml  ← NOVO                  │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                              │                                          │
│                              │ ArgoCD detecta mudança na main           │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  AKS (cluster Kubernetes na Azure — 24/7)                       │    │
│  │                                                                 │    │
│  │  4. ArgoCD puxa os YAMLs atualizados do Git                    │    │
│  │     → kubectl apply -f claims/prod/claim-storage-app-x.yaml    │    │
│  │                                                                 │    │
│  │  5. Crossplane recebe o Claim                                   │    │
│  │     → Lê a Composition (como criar)                             │    │
│  │     → Autentica na Azure (Workload Identity, sem senha)         │    │
│  │     → Chama a API da Azure                                      │    │
│  │                                                                 │    │
│  │  6. Recursos criados na Azure                                   │    │
│  │     → Resource Group: rg-app-x                                  │    │
│  │     → Storage Account: stappx                                   │    │
│  │     → Status: READY: True ✅                                     │    │
│  │                                                                 │    │
│  │  7. Reconciliação contínua 24/7                                 │    │
│  │     → Se alguém deletar no portal Azure → recria                │    │
│  │     → Se alguém alterar no portal → reverte                     │    │
│  │     → Se alguém mudar o YAML no Git → atualiza                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Como o dev se conecta ao cluster de produção

```bash
# 1. Login na Azure (uma vez)
az login

# 2. Baixar kubeconfig do AKS de produção
az aks get-credentials --resource-group rg-plataforma --name aks-prod

# 3. Verificar em qual cluster está conectado
kubectl config current-context
# Resultado: aks-prod

# 4. Agora kubectl fala com o AKS na nuvem
kubectl get storagebucket     # ver Claims
kubectl get resourcegroup     # ver RGs
kubectl get account           # ver Storage Accounts

# 5. Trocar de volta para o Kind local
kubectl config use-context kind-crossplane-dev
```

### Múltiplos clusters no kubeconfig

```
~/.kube/config (arquivo no laptop do dev)
│
├── context: kind-crossplane-dev
│   └── server: https://127.0.0.1:39135           ← cluster local (Docker)
│
├── context: aks-prod
│   └── server: https://aks-prod.eastus.azmk8s.io ← cluster na Azure (produção)
│
└── context: aks-staging
    └── server: https://aks-stg.eastus.azmk8s.io  ← outro cluster na Azure

# Trocar entre clusters:
kubectl config use-context kind-crossplane-dev   ← local
kubectl config use-context aks-staging           ← staging
kubectl config use-context aks-prod              ← produção
```

### Resumo: Local vs Produção

| Aspecto | Local (Kind) | Produção (AKS + GitOps) |
|---|---|---|
| **Cluster** | Kind no Docker do laptop | AKS na Azure, 24/7 |
| **Quem aplica YAMLs** | Dev: `kubectl apply` manual | ArgoCD: automático via Git |
| **Conta Azure** | Sandbox/dev (gastos limitados) | Produção |
| **Review** | Nenhum (teste pessoal) | PR review obrigatório |
| **Autenticação** | Service Principal + senha | Workload Identity (sem senha) |
| **Reconciliação** | Só com laptop ligado | Contínua, 24/7 |
| **Drift correction** | Só com Kind rodando | Automática e permanente |
| **Permissão do dev** | Full access (é local) | Read-only (só leitura) |

---

## Autenticação em Produção vs Local

### Níveis de maturidade

```
Nível 1 — Service Principal com senha (o que fizemos no lab)
    ├── clientId + clientSecret em um Secret do Kubernetes
    ├── Senha expira, precisa rotacionar manualmente
    └── ⚠️ Risco: senha pode vazar no Git
    └── ✅ Aceitável para: lab, dev local, sandbox

Nível 2 — Service Principal com certificado
    ├── Usa certificado X.509 ao invés de senha
    └── Mais seguro, mas ainda precisa rotacionar

Nível 3 — Workload Identity / Managed Identity (padrão ouro)
    ├── SEM senha, SEM certificado, SEM secret
    ├── O próprio AKS se autentica na Azure automaticamente
    ├── A Azure "confia" no pod pelo identity federation
    └── Nada para rotacionar, nada para vazar
    └── ✅ Recomendado para: staging, produção
```

### Como funciona o Workload Identity

```
AKS (cluster na Azure)
│
├── Pod do Crossplane
│   └── ServiceAccount: crossplane-sa
│       └── Anotação: azure.workload.identity/client-id: "xxx"
│           │
│           ▼
│   Azure AD verifica:
│   "Esse ServiceAccount desse AKS está autorizado?"
│           │
│           ▼
│   Sim → Gera token temporário automaticamente
│           │
│           ▼
│   Crossplane usa o token para criar recursos
│   Token expira e é renovado automaticamente
│
└── NENHUMA senha armazenada em lugar nenhum
```

### Onde ficam as credenciais em empresas de alto padrão

| Componente | Onde ficam as credenciais | Tem senha? |
|---|---|---|
| **Crossplane no AKS** | Workload Identity (federação com Azure AD) | ❌ Não |
| **ArgoCD** | ServiceAccount do Kubernetes com RBAC | ❌ Não |
| **CI/CD (GitHub Actions)** | OIDC federation com Azure AD | ❌ Não |
| **Secrets de aplicação** | Azure Key Vault (injetados via CSI driver) | Isolado |
| **Dev local (Kind)** | Service Principal com senha | ✅ Sim (aceitável) |

### Quem acessa o quê em produção

| Persona | Como acessa | Permissão no cluster |
|---|---|---|
| **Dev** | `az login` + `az aks get-credentials` | Read-only (só ver) |
| **Lead/SRE** | Mesmo fluxo | Read-write em staging, limitado em prod |
| **ArgoCD** | ServiceAccount automático | Full access para aplicar YAMLs |
| **Admin/Plataforma** | Conta privilegiada Azure AD | Full access |

---

## Onde encontrar Providers e Documentação

### Marketplace Upbound (principal referência)

- **URL**: [https://marketplace.upbound.io](https://marketplace.upbound.io)
- Aqui você encontra todos os providers oficiais, suas versões, e a **referência completa** de cada recurso (apiVersion, kind, campos do spec)

### Providers que usamos neste lab

| Provider | Pacote | Marketplace |
|---|---|---|
| Provider Family Azure | `xpkg.upbound.io/upbound/provider-family-azure` | [Link](https://marketplace.upbound.io/providers/upbound/provider-family-azure) |
| Provider Azure Storage | `xpkg.upbound.io/upbound/provider-azure-storage` | [Link](https://marketplace.upbound.io/providers/upbound/provider-azure-storage) |

### Outros providers populares

| Provider | Pacote |
|---|---|
| AWS Family | `xpkg.upbound.io/upbound/provider-family-aws` |
| GCP Family | `xpkg.upbound.io/upbound/provider-family-gcp` |
| Azure Network | `xpkg.upbound.io/upbound/provider-azure-network` |
| Azure Compute | `xpkg.upbound.io/upbound/provider-azure-compute` |

### Como descobrir os campos do YAML

```bash
# Listar todos os CRDs do Azure instalados
kubectl get crds | grep azure

# Ver a documentação de um recurso específico
kubectl explain resourcegroup
kubectl explain resourcegroup.spec
kubectl explain resourcegroup.spec.forProvider

# Validar sem aplicar
kubectl apply --dry-run=client -f meu-recurso.yaml
```

### Documentação oficial

- **Crossplane docs**: [https://docs.crossplane.io](https://docs.crossplane.io)
- **Upbound docs**: [https://docs.upbound.io](https://docs.upbound.io)
- **GitHub do Crossplane**: [https://github.com/crossplane/crossplane](https://github.com/crossplane/crossplane)

---

## Passo a Passo do que fizemos

### Etapa 1 — Criar o cluster Kubernetes local

```bash
# Baixar o Kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Criar o cluster
kind create cluster --name crossplane-lab
```

**Por quê?** O Crossplane precisa de um cluster Kubernetes para rodar. O Kind cria um cluster local usando Docker.

### Etapa 2 — Instalar o Crossplane via Helm

```bash
helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update

helm install crossplane \
  crossplane-stable/crossplane \
  --namespace crossplane-system \
  --create-namespace \
  --wait
```

**Por quê?** O Helm instala o Crossplane como pods no cluster, no namespace `crossplane-system`.

### Etapa 3 — Instalar os Providers do Azure

Arquivos criados:
- `provider-azure.yaml` — Provider Family (base)
- `provider-azure-storage.yaml` — Provider de Storage

```bash
kubectl apply -f provider-azure.yaml
kubectl apply -f provider-azure-storage.yaml
kubectl get providers  # verificar instalação
```

**Por quê?** Os providers são plugins que ensinam o Crossplane a se comunicar com a Azure. Eles registram CRDs (novos tipos de recursos) no Kubernetes.

### Etapa 4 — Criar o Service Principal no Azure

```bash
# Criar o SP
az ad sp create-for-rbac --name crossplane-labs-sp > azure-credentials.json

# Obter o Object ID
OBJ_ID=$(az ad sp show --id "APP_ID_AQUI" --query id -o tsv)

# Atribuir role Contributor
az role assignment create \
  --assignee-object-id "$OBJ_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/SEU_SUBSCRIPTION_ID"
```

**Por quê?** O Crossplane precisa de credenciais para autenticar na Azure. O Service Principal é uma "conta de serviço" com permissão Contributor na subscription.

### Etapa 5 — Criar o Secret no Kubernetes

```bash
# Arquivo de credenciais no formato do Crossplane
cat > azure-credentials.txt <<EOF
{
  "clientId": "SEU_APP_ID",
  "clientSecret": "SUA_PASSWORD",
  "subscriptionId": "SEU_SUBSCRIPTION_ID",
  "tenantId": "SEU_TENANT_ID"
}
EOF

# Criar o Secret
kubectl create secret generic azure-secret \
  -n crossplane-system \
  --from-file=creds=./azure-credentials.txt
```

**Por quê?** O Secret armazena as credenciais de forma segura dentro do Kubernetes. O Crossplane lê desse Secret quando precisa autenticar na Azure.

> **Atenção:** os nomes dos campos mudam entre o `az cli` e o Crossplane:
> - `appId` → `clientId`
> - `password` → `clientSecret`
> - `tenant` → `tenantId`
> - *(precisa adicionar)* → `subscriptionId`

### Etapa 6 — Criar o ProviderConfig

Arquivo: `provider-config-azure.yaml`

```bash
kubectl apply -f provider-config-azure.yaml
```

**Por quê?** O ProviderConfig conecta o Provider ao Secret. Ele diz: "quando for criar recursos na Azure, use as credenciais do Secret `azure-secret`".

### Etapa 7 — Criar recursos na Azure

Arquivo: `resource-group.yaml`

```bash
kubectl apply -f resource-group.yaml
kubectl get resourcegroup  # verificar status
```

**Por quê?** Agora sim o Crossplane cria o recurso na Azure de verdade. O Resource Group aparece tanto no Kubernetes (`kubectl get resourcegroup`) quanto na Azure (`az group show`).

### Etapa 8 — Registrar Resource Providers na Azure

```bash
# Se aparecer erro MissingSubscriptionRegistration, registre o provider:
az provider register --namespace Microsoft.Storage

# Verificar se registrou:
az provider show --namespace Microsoft.Storage --query "registrationState" -o tsv
# Resultado esperado: Registered
```

**Por quê?** Na Azure, cada subscription precisa ter os resource providers habilitados antes de criar recursos daquele tipo. Em contas novas/free, nem todos estão registrados por padrão.

### Etapa 9 — Instalar a Function e criar XRD + Composition

```bash
# Instalar a function (necessária para Pipeline mode)
cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1beta1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.upbound.io/crossplane-contrib/function-patch-and-transform:v0.7.0
EOF

# Verificar se está healthy
kubectl get functions

# Aplicar XRD (registra o novo tipo StorageBucket)
kubectl apply -f xrd-storagebucket.yaml

# Aplicar Composition (define como implementar o StorageBucket)
kubectl apply -f composition-storagebucket.yaml
```

**Por quê?** O XRD cria uma API customizada. A Composition define o que será criado na Azure quando alguém usar essa API. A Function é necessária para o Pipeline mode.

### Etapa 10 — Criar recurso via Claim

```bash
# Aplicar o Claim (cria Resource Group + Storage Account automaticamente)
kubectl apply -f claim-storagebucket.yaml

# Acompanhar
kubectl get storagebucket
kubectl get resourcegroup,account
```

**Por quê?** O Claim é a forma simplificada de criar recursos. O dev só precisa informar environment, location e storageClass — a Composition cuida do resto.

---

## Comandos úteis de referência

```bash
# === CLUSTER ===
kind create cluster --name meu-cluster    # criar cluster
kind delete cluster --name meu-cluster    # destruir cluster
kubectl cluster-info                       # verificar cluster

# === CROSSPLANE ===
kubectl get providers                      # listar providers instalados
kubectl get providerconfig                 # listar configs
kubectl get functions                      # listar functions instaladas
kubectl get crds | grep azure             # ver CRDs disponíveis

# === XRD / COMPOSITION / CLAIM ===
kubectl get xrd                            # listar XRDs
kubectl get composition                    # listar Compositions
kubectl get storagebucket                  # listar Claims (tipo StorageBucket)
kubectl get xstoragebucket                # listar Composite Resources

# === RECURSOS ===
kubectl apply -f arquivo.yaml             # criar/atualizar recurso
kubectl delete -f arquivo.yaml            # deletar recurso (e na Azure!)
kubectl get resourcegroup                  # verificar status
kubectl describe resourcegroup NOME       # detalhes e eventos
kubectl explain resourcegroup.spec        # documentação dos campos
kubectl apply --dry-run=client -f x.yaml  # validar sem criar

# === DEBUG ===
kubectl get pods -n crossplane-system                     # verificar pods do Crossplane
kubectl logs -n crossplane-system -l app=crossplane       # logs do Crossplane
kubectl get events --sort-by='.lastTimestamp'              # eventos recentes
kubectl describe xstoragebucket NOME | tail -20          # erros do composite

# === AZURE ===
az group list -o table                     # listar RGs na Azure
az group show --name rg-crossplane-lab01  # verificar RG específico
az provider register --namespace X        # registrar resource provider
az provider show --namespace X --query "registrationState"  # verificar registro
```

---

## Estrutura dos arquivos do lab

```
lab-01/
├── provider-azure.yaml            # Provider Family Azure
├── provider-azure-storage.yaml    # Provider Azure Storage
├── provider-config-azure.yaml     # ProviderConfig com credenciais
├── resource-group.yaml            # Resource Group direto na Azure
├── storageaccount.yaml            # Storage Account direto na Azure
├── xrd-storagebucket.yaml         # XRD — define a API "StorageBucket"
├── composition-storagebucket.yaml # Composition — implementa o XRD (Pipeline mode)
├── claim-storagebucket.yaml       # Claim — o dev usa para criar recursos
├── azure-credentials.json         # Credenciais do SP (formato az cli)
└── azure-credentials.txt          # Credenciais do SP (formato Crossplane)
```

> **⚠️ Segurança:** Os arquivos `azure-credentials.json` e `azure-credentials.txt` contêm senhas. **Nunca suba para o Git.** Adicione ao `.gitignore`:
> ```
> azure-credentials.*
> ```

---

## Troubleshooting — Problemas comuns

### `Kubernetes cluster unreachable`
**Causa:** Nenhum cluster rodando.
**Solução:** `kind create cluster --name crossplane-lab`

### `cannot re-use a name that is still in use`
**Causa:** O Helm release já existe.
**Solução:** `helm list -n crossplane-system` para confirmar. Use `helm upgrade` se quiser atualizar.

### `MissingSubscriptionRegistration`
**Causa:** O resource provider não está habilitado na subscription Azure.
**Solução:**
```bash
az provider register --namespace Microsoft.Storage
az provider show --namespace Microsoft.Storage --query "registrationState" -o tsv
```

### `AccountNameInvalid`
**Causa:** Nome do Storage Account inválido (hífens, muito longo, etc.).
**Regras:** 3-24 caracteres, só letras minúsculas e números.
**Solução:** Usar nomes curtos e sem hífens.

### `cannot find an active FunctionRevision`
**Causa:** A `function-patch-and-transform` não está instalada.
**Solução:**
```bash
cat <<EOF | kubectl apply -f -
apiVersion: pkg.crossplane.io/v1beta1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.upbound.io/crossplane-contrib/function-patch-and-transform:v0.7.0
EOF
```

### `ResourceGroupNotFound`
**Causa:** O Storage Account está tentando ser criado antes do Resource Group ficar Ready.
**Solução:** Aguardar — o Crossplane reconcilia automaticamente e tenta novamente.

### `Operation returned an invalid status 'Bad Request'` (role assignment)
**Causa:** Problema ao atribuir role via `az role assignment create`.
**Solução:** Usar `--assignee-object-id` com `--assignee-principal-type`:
```bash
OBJ_ID=$(az ad sp show --id "SEU_APP_ID" --query id -o tsv)
az role assignment create \
  --assignee-object-id "$OBJ_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/SEU_SUBSCRIPTION_ID"
```

### `unknown name "truncate"` no Pipeline
**Causa:** A versão da function não suporta o transform `Truncate`.
**Solução:** Remover o Truncate e usar nomes mais curtos no Claim.
