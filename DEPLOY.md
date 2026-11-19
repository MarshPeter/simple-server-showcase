# Deploying the Class To-Do Board

This guide takes the project from your laptop to a public HTTPS URL with live logs:

```
Students' browsers ──HTTPS──> Azure Container Apps ──TLS──> Neon Postgres
                                   ▲
                                   │ pulls the image
                     GitHub Container Registry (ghcr.io)
                                   ▲
                                   │ builds on every push
                            GitHub Actions
```

| Piece | Job | Expected cost |
|---|---|---|
| **Neon** | Hosts the Postgres database | Free plan |
| **GitHub + GitHub Actions** | Stores the code and builds the Docker image | Free |
| **GitHub Container Registry (GHCR)** | Stores the built image | Free for public images |
| **Azure Container Apps** | Runs the container and gives you the URL, HTTPS and logs | About $0 when it sleeps between classes. Keeping it awake all month costs a few dollars. |

You **don't need Docker on your machine** to deploy, because GitHub Actions builds the image for you. Docker is only for testing locally.

Plan for about 45 minutes the first time. After that, shipping a change takes one `git push` and one command.

---

## 0. Before you start

You need:

- A **GitHub account**.
- An **Azure account with an active subscription**. A free account or Pay-As-You-Go both work.
- A **Neon account** from https://neon.tech. Signing in with GitHub is fine.
- These tools in your WSL terminal: `git`, `gh` (GitHub CLI) and `az` (Azure CLI). All three are already installed.

Log the CLIs in once:

```bash
gh auth login
```

```bash
az login
```

If you have more than one Azure subscription, choose the right one:

```bash
az account list -o table
```

```bash
az account set --subscription "<subscription name or id>"
```

---

## 1. Create the database (Neon)

1. Go to https://console.neon.tech → **New project**.
   - **Name:** `class-todo`
   - **Postgres version:** the default
   - **Region:** **AWS Asia Pacific (Sydney)**, close to the Azure region used below. If you're deploying somewhere else, pick the Neon region nearest your Azure region.
2. When the project opens, click **Connect**.
   - Turn **Connection pooling** **on**. The host name will contain `-pooler`.
   - Copy the connection string. It looks like:
     ```
     postgresql://neondb_owner:XXXX@ep-cool-name-123456-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
     ```
   - Keep `sslmode=require` on the end. Treat the string like a password: it contains the database password.

You don't need to create any tables. The app creates the `todos` table the first time it gets a request.

> **About Neon's free plan:** the database sleeps after about 5 idle minutes. The first query after that takes about a second to wake it, which is fine for a classroom.

---

## 2. Put the code on GitHub

From the project folder:

```bash
cd ~/workspace/github/simple-server-showcase
git init -b main
git add .
git commit -m "Class To-Do Board"
```

Create the GitHub repo and push in one step. Use `--private` instead of `--public` if you prefer; step 3 covers both cases.

```bash
gh repo create simple-server-showcase --public --source . --push
```

The push starts the **Build image** workflow (`.github/workflows/docker.yml`). Watch it finish (about 2 minutes):

```bash
gh run watch
```

When it's green, your image is at `ghcr.io/<your-github-username>/simple-server-showcase` with two tags:
- `:latest`
- `:<commit-sha>`, which is what you'll deploy so every version is traceable

---

## 3. Let Azure pull the image

**Option A: make the image public (simplest).** The image contains only the app code, no secrets.

1. On GitHub, open your profile → **Packages** → `simple-server-showcase`.
2. **Package settings** → **Danger Zone** → **Change visibility** → **Public**.

**Option B: keep it private.** Create a GitHub *classic* personal access token with only the `read:packages` scope (GitHub → Settings → Developer settings → Personal access tokens). You'll pass it to Azure in step 4 (see the note there).

---

## 4. Create the app on Azure Container Apps

Set a few shell variables first, so the rest can be copied as-is. Run these in the same terminal you'll use for the remaining steps.

```bash
RG=class-todo-rg
LOC=australiaeast
ENV=class-todo-env
APP=class-todo
OWNER=$(gh api user -q .login | tr '[:upper:]' '[:lower:]')
IMAGE=ghcr.io/$OWNER/simple-server-showcase
```

Enter the secrets without them appearing on screen or in your shell history. Paste the Neon string when prompted.

```bash
read -rsp "Neon connection string: " DATABASE_URL; echo
```

The next command generates a random reset token. Save the printed value in your password manager: you need it to clear the board between classes.

```bash
RESET_TOKEN=$(openssl rand -hex 16); echo "Reset token: $RESET_TOKEN"
```

### 4a. One-time Azure setup

```bash
az extension add --name containerapp --upgrade
```

```bash
az provider register --namespace Microsoft.App --wait
```

```bash
az provider register --namespace Microsoft.OperationalInsights --wait
```

### 4b. Resource group and Container Apps environment

The resource group is a folder holding everything for this project, which makes cleanup a single command. The environment is the shared network and logging home for the app. Creating it also creates a Log Analytics workspace, which stores past logs.

```bash
az group create --name $RG --location $LOC
```

```bash
az containerapp env create --name $ENV --resource-group $RG --location $LOC
```

This takes a few minutes.

### 4c. Create the app

```bash
az containerapp create \
  --name $APP \
  --resource-group $RG \
  --environment $ENV \
  --image $IMAGE:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 0.25 --memory 0.5Gi \
  --min-replicas 0 --max-replicas 1 \
  --secrets "database-url=$DATABASE_URL" "reset-token=$RESET_TOKEN" \
  --env-vars DATABASE_URL=secretref:database-url RESET_TOKEN=secretref:reset-token MAX_TODOS=200 \
  --query properties.configuration.ingress.fqdn -o tsv
```

What the settings mean:

| Setting | Why |
|---|---|
| `--target-port 8000` | The port gunicorn listens on inside the container (see `Dockerfile`). |
| `--ingress external` | Gives the app a public HTTPS URL. Azure handles the certificate. |
| `--cpu 0.25 --memory 0.5Gi` | The smallest size, plenty for a class. |
| `--min-replicas 0` | The app sleeps when nobody uses it, so it costs almost nothing. See section 6 to wake it before class. |
| `--max-replicas 1` | Never more than one copy, so costs can't run away. One copy easily handles a classroom. |
| `--secrets` + `secretref:` | The database password and reset token are stored encrypted in Azure, not in the image. |

> **If you chose Option B (private image),** add these lines to the command above:
> ```
>   --registry-server ghcr.io \
>   --registry-username $OWNER \
>   --registry-password <the read:packages token> \
> ```

The command prints the app's address, something like `class-todo.happyfield-1234abcd.australiaeast.azurecontainerapps.io`. To get it again later:

```bash
az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv
```

### 4d. Check it works

```bash
URL=https://$(az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)
curl $URL/api/health
```

You should get `{"status":"ok"}`. The first call may take a few seconds while the app wakes up.

```bash
curl $URL/api/todos
```

You should get `[]`, which means the database connection works. Now open the URL in a browser, add a to-do, and check that it appears in the Neon console (**Tables** → `todos`).

---

## 5. Watch the live logs

Each request prints one line, for example:

```
2026-11-19 09:15:02 INFO POST /api/todos 201 38ms ip=203.0.113.7 body={"title": "Do Dishes", "author": "Sam"}
```

**Terminal (best for the projector):**

```bash
az containerapp logs show -n $APP -g $RG --follow --tail 30 --format text
```

**Browser:** Azure Portal → your Container App → **Monitoring** → **Log stream**.

**Startup problems** (image won't pull, container keeps restarting) appear in the *system* logs:

```bash
az containerapp logs show -n $APP -g $RG --type system --tail 50
```

**Older logs:** Portal → Container App → **Monitoring** → **Logs**. These are kept in Log Analytics.

> The log stream only shows something while the app is running. If it says no replicas are running, open the site once to wake it up, or warm it up as in section 6.

---

## 6. Before and after each class

### Warm it up about 5 minutes before class (no cold starts)

```bash
az containerapp update -n $APP -g $RG --min-replicas 1
```

Then open the site once, which also wakes the Neon database.

### Clear the board

```bash
curl -X POST -H "X-Reset-Token: $RESET_TOKEN" $URL/api/reset
```

If you've opened a new terminal since step 4, re-run the variable lines from step 4 and paste the saved token into `RESET_TOKEN`.

### Let it sleep after class

```bash
az containerapp update -n $APP -g $RG --min-replicas 0
```

Forgetting this isn't a disaster: a single always-on minimum-size replica costs roughly a few dollars a month after the free allowance. It's still worth doing.

---

## 7. Shipping changes

1. Edit, commit and push:
   ```bash
   git commit -am "Describe the change"
   ```
   ```bash
   git push
   ```
2. Wait for the image build:
   ```bash
   gh run watch
   ```
3. Deploy that exact commit:
   ```bash
   az containerapp update -n $APP -g $RG --image $IMAGE:$(git rev-parse HEAD)
   ```

Deploying the commit tag (not `:latest`) matters. Azure only starts a new version when the image name changes, so re-deploying `:latest` may do nothing. Each deploy creates a new *revision*.

**To roll back**, deploy an older commit:

```bash
az containerapp update -n $APP -g $RG --image $IMAGE:<older-commit-sha>
```

---

## 8. Changing settings or secrets

Change a normal setting:

```bash
az containerapp update -n $APP -g $RG --set-env-vars MAX_TODOS=100
```

Change a secret, such as a new Neon password:

```bash
read -rsp "New Neon connection string: " DATABASE_URL; echo
az containerapp secret set -n $APP -g $RG --secrets "database-url=$DATABASE_URL"
```

A new secret only takes effect after a restart:

```bash
az containerapp revision restart -n $APP -g $RG \
  --revision $(az containerapp revision list -n $APP -g $RG --query "[?properties.active].name | [0]" -o tsv)
```

---

## 9. Cost safety net (recommended)

Set a budget alert so a surprise can't go unnoticed:

1. Azure Portal → **Cost Management** → **Budgets** → **Add**.
2. **Scope:** your subscription (or just `class-todo-rg`).
3. **Amount:** e.g. $5/month.
4. **Alerts:** email at 50% and 100%.

Things that keep costs at about $0:
- `--min-replicas 0` outside class
- `--max-replicas 1`
- the smallest CPU and memory
- a public GHCR image instead of Azure Container Registry, which costs about $5/month

The Azure Container Apps consumption plan includes a monthly free allowance of CPU time, memory time and requests, which a classroom app sits comfortably inside. Current numbers are on the [Container Apps pricing page](https://azure.microsoft.com/pricing/details/container-apps/) and the [Neon pricing page](https://neon.tech/pricing).

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Site takes 5–15 s on the first visit | App was asleep (`min-replicas 0`) | Expected. Warm it up before class (section 6). |
| System logs show `ImagePullBackOff` or "unauthorized" | GHCR package is private | Make it public (step 3, Option A) or add registry credentials (Option B). |
| `/api/health` works but `/api/todos` returns an error | Bad `DATABASE_URL` | Check the live log for the Python error. Re-set the secret and restart (section 8). Make sure the string ends with `sslmode=require`. |
| Logs show `password authentication failed` | Neon password was reset | Copy a fresh string from Neon **Connect**, then run section 8. |
| Error saying "The board is full" | Hit `MAX_TODOS` | Clear the board (section 6) or raise `MAX_TODOS` (section 8). |
| `az containerapp` says the command isn't found | Extension missing | `az extension add --name containerapp --upgrade` |
| A deploy didn't change anything | Re-deployed the same image tag | Deploy `:$(git rev-parse HEAD)`, not `:latest` (section 7). |
| The log stream is empty | No replica running | Open the site once to wake it, or set `--min-replicas 1`. |

---

## 11. Removing everything

This deletes the app, its environment and its logs, and stops all Azure charges:

```bash
az group delete --name class-todo-rg --yes
```

Delete the Neon project from its **Settings** page, and the GitHub repo and package from their settings pages if you want them gone too.

---

## Moving off Azure later

The same image runs anywhere that runs Docker. It needs:
- Port 8000 exposed.
- `DATABASE_URL` set. `RESET_TOKEN` and `MAX_TODOS` are optional.

For example, on any VPS:

```bash
docker run -d -p 80:8000 -e DATABASE_URL='<neon string>' ghcr.io/<owner>/simple-server-showcase:latest
```

Render, Fly.io and Google Cloud Run take the same image and the same environment variables.
