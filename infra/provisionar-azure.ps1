<#
.SYNOPSIS
    Provisiona no Azure os recursos para hospedar o DocumentAI e publicar pelo GitHub Actions via OIDC.

.DESCRIPTION
    Cria (ou atualiza, se já existirem):
      1. Grupo de recursos.
      2. Plano do App Service Linux no nível gratuito (F1).
      3. App Service com runtime .NET 10, somente HTTPS, TLS 1.2+, FTP desabilitado e logs de aplicação.
      4. Identidade gerenciada atribuída pelo usuário, usada pelo GitHub Actions.
      5. Credencial federada (OIDC) que só aceita tokens do environment "production" do repositório.
      6. Permissão "Website Contributor" restrita ao App Service (menor privilégio).

    Não cria segredos: a autenticação do pipeline é federada, sem senha ou chave de longa duração.
    Requer Azure CLI autenticado (az login) com permissão de Owner ou User Access Administrator na assinatura.

.EXAMPLE
    ./infra/provisionar-azure.ps1 -Assinatura "<id-da-assinatura>"
#>
param(
    [Parameter(Mandatory)] [string] $Assinatura,
    # A cota do plano gratuito (F1) varia por região; em brazilsouth e eastus2 ela é 0 em assinaturas novas.
    [string] $Regiao = "centralus",
    [string] $GrupoRecursos = "rg-documentai",
    [string] $Plano = "asp-documentai-free",
    [string] $NomeApp = "documentai-gmaurity",
    [string] $Identidade = "id-documentai-github",
    [string] $Repositorio = "GabrielMaurity/DocumentAI",
    [string] $AmbienteGitHub = "production"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

function Etapa([string] $texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }

Etapa "Selecionando a assinatura"
az account set --subscription $Assinatura
$tenant = az account show --query tenantId -o tsv

Etapa "Registrando os provedores de recursos necessários"
foreach ($provedor in "Microsoft.Web", "Microsoft.ManagedIdentity") {
    az provider register --namespace $provedor --wait | Out-Null
}

Etapa "Grupo de recursos $GrupoRecursos"
if ((az group exists --name $GrupoRecursos) -ne "true") {
    az group create --name $GrupoRecursos --location $Regiao --output none
}

Etapa "Plano $Plano (F1 gratuito, Linux)"
az appservice plan create --name $Plano --resource-group $GrupoRecursos --location $Regiao --sku F1 --is-linux --output none

Etapa "App Service $NomeApp (.NET 10)"
$existe = az webapp list --resource-group $GrupoRecursos --query "[?name=='$NomeApp'] | length(@)" -o tsv
if ($existe -eq "0") {
    az webapp create --name $NomeApp --resource-group $GrupoRecursos --plan $Plano --runtime "DOTNETCORE:10.0" --output none
}

Etapa "Configurações de segurança e ambiente"
az webapp update --name $NomeApp --resource-group $GrupoRecursos --https-only true --output none
az webapp config set --name $NomeApp --resource-group $GrupoRecursos `
    --min-tls-version 1.2 --ftps-state Disabled --http20-enabled true --output none
az webapp config appsettings set --name $NomeApp --resource-group $GrupoRecursos `
    --settings ASPNETCORE_ENVIRONMENT=Production --output none
az webapp log config --name $NomeApp --resource-group $GrupoRecursos `
    --docker-container-logging filesystem --output none

Etapa "Identidade $Identidade e credencial federada do GitHub Actions"
az identity create --name $Identidade --resource-group $GrupoRecursos --location $Regiao --output none
$clientId = az identity show --name $Identidade --resource-group $GrupoRecursos --query clientId -o tsv
$principalId = az identity show --name $Identidade --resource-group $GrupoRecursos --query principalId -o tsv

$sujeito = "repo:${Repositorio}:environment:${AmbienteGitHub}"
$credencialExiste = az identity federated-credential list --identity-name $Identidade --resource-group $GrupoRecursos `
    --query "[?subject=='$sujeito'] | length(@)" -o tsv
if ($credencialExiste -eq "0") {
    az identity federated-credential create --name "github-$AmbienteGitHub" `
        --identity-name $Identidade --resource-group $GrupoRecursos `
        --issuer "https://token.actions.githubusercontent.com" `
        --subject $sujeito --audiences "api://AzureADTokenExchange" --output none
}

Etapa "Permissão Website Contributor restrita ao App Service"
$escopo = az webapp show --name $NomeApp --resource-group $GrupoRecursos --query id -o tsv
# A consulta tem espaços de propósito: sem eles, o cmd do Windows interpreta os parênteses ao chamar az.cmd.
$atribuicaoExiste = az role assignment list --assignee $principalId --scope $escopo `
    --query "[?roleDefinitionName == 'Website Contributor'] | length(@)" -o tsv
if ($atribuicaoExiste -eq "0") {
    az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal `
        --role "Website Contributor" --scope $escopo --output none
}

$url = "https://" + (az webapp show --name $NomeApp --resource-group $GrupoRecursos --query defaultHostName -o tsv)

Etapa "Concluído"
Write-Host "URL do App Service : $url"
Write-Host "Documentação       : $url/scalar"
Write-Host ""
Write-Host "Configure no repositório GitHub (environment '$AmbienteGitHub'):"
Write-Host "  secret   AZURE_CLIENT_ID       = $clientId"
Write-Host "  secret   AZURE_TENANT_ID       = $tenant"
Write-Host "  secret   AZURE_SUBSCRIPTION_ID = $Assinatura"
Write-Host "  variável AZURE_WEBAPP_NAME     = $NomeApp"
