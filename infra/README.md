# Infrastructure Deployment

Azure Static Web Apps deployment for stepinto.dev blog.

## Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- Azure subscription
- Logged in via `az login`

## Deployment

### 1. Create Resource Group (if needed)

```bash
az group create --name stepinto-dev-rg --location westeurope
```

### 2. Deploy Infrastructure

```bash
az deployment group create \
  --resource-group stepinto-dev-rg \
  --template-file main.bicep \
  --parameters main.bicepparam
```

### 3. Get Deployment Token

After deployment, grab the deployment token for GitHub Actions:

```bash
az staticwebapp secrets list \
  --name stepinto-dev-blog \
  --resource-group stepinto-dev-rg \
  --query "properties.apiKey" -o tsv
```

Add this as `AZURE_STATIC_WEB_APPS_API_TOKEN` secret in your GitHub repository.

## DNS Configuration (DNSimple)

Azure Static Web Apps requires DNS validation for custom domains.

### For Root Domain (stepinto.dev)

1. **Get the validation token** from Azure Portal:
   - Go to your Static Web App
   - Custom domains → Add
   - Enter `stepinto.dev`
   - Note the TXT record value shown

2. **In DNSimple**, add these records:

   | Type | Name | Value |
   |------|------|-------|
   | ALIAS | (blank/root) | `<your-swa>.azurestaticapps.net` |
   | TXT | (blank/root) | `<validation-token-from-azure>` |

3. **Wait for validation** (usually 5-15 minutes)

4. **Verify in Azure Portal** — the custom domain should show as "Ready"

### Using the DNSimple API

If you prefer automation, here's how to set the records via API:

```bash
# Set your credentials
DNSIMPLE_TOKEN="your_api_token"
ACCOUNT_ID="your_account_id"  # Find in DNSimple dashboard
DOMAIN="stepinto.dev"

# Add ALIAS record for root domain
curl -X POST \
  -H "Authorization: Bearer $DNSIMPLE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "",
    "type": "ALIAS",
    "content": "stepinto-dev-blog.azurestaticapps.net",
    "ttl": 3600
  }' \
  "https://api.dnsimple.com/v2/$ACCOUNT_ID/zones/$DOMAIN/records"

# Add TXT record for validation
curl -X POST \
  -H "Authorization: Bearer $DNSIMPLE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "",
    "type": "TXT",
    "content": "<validation-token-from-azure>",
    "ttl": 3600
  }' \
  "https://api.dnsimple.com/v2/$ACCOUNT_ID/zones/$DOMAIN/records"
```

**Note**: Replace `<validation-token-from-azure>` with the actual token shown in Azure Portal.

## SSL

SSL certificates are automatically provisioned and renewed by Azure Static Web Apps once DNS is validated. No action required.

## Cost

The **Free** tier includes:
- 100 GB bandwidth/month
- 2 custom domains
- Free SSL
- GitHub/Azure DevOps integration

More than enough for a personal blog.

## Troubleshooting

### Custom domain stuck on "Validating"

- Ensure DNS records are correct (check with `dig stepinto.dev`)
- DNS propagation can take up to 48 hours (usually much faster)
- Try removing and re-adding the custom domain in Azure

### Build failures

- Check Hugo version compatibility in workflow
- Ensure theme submodule is properly initialised
- Review build logs in Azure Portal → Static Web App → Deployment history

