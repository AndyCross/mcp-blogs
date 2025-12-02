// Azure Static Web App for Hugo blog
// Deploy with: az deployment group create -g <resource-group> -f main.bicep -p main.bicepparam

@description('Name of the Static Web App')
param staticWebAppName string = 'stepinto-dev-blog'

@description('Location for the Static Web App')
param location string = 'westeurope'

@description('SKU for the Static Web App')
@allowed([
  'Free'
  'Standard'
])
param sku string = 'Free'

@description('Custom domain to configure (optional)')
param customDomain string = 'stepinto.dev'

// Static Web App resource
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: location
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    buildProperties: {
      appLocation: '/'
      outputLocation: 'public'
      appBuildCommand: 'hugo --minify'
    }
  }
  tags: {
    project: 'stepinto-dev'
    purpose: 'blog'
  }
}

// Custom domain configuration
// Note: DNS must be configured first before this will validate
resource customDomainResource 'Microsoft.Web/staticSites/customDomains@2023-12-01' = if (customDomain != '') {
  parent: staticWebApp
  name: customDomain
  properties: {}
}

// Outputs
output staticWebAppName string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output deploymentToken string = listSecrets(staticWebApp.id, staticWebApp.apiVersion).properties.apiKey

