terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-platform-terraform-prod"
    storage_account_name = "stplatformtfstatestbprod"
    container_name       = "tfstates"
    key                  = "gdd-veille.tfstate"
    subscription_id      = "70d5f67e-2e75-416d-a322-457493d18263"
  }
}

provider "azurerm" {
  subscription_id = "cef4660c-cb19-43f7-b3f3-c6575a4f836a"
  features {}
}

# Provider pour l'accès aux ressources de management (Logs, TFState)
provider "azurerm" {
  alias           = "management"
  subscription_id = "70d5f67e-2e75-416d-a322-457493d18263"
  features {}
}

# ------------------------------------------------------------------------------
# DATA SOURCES & EXTERNAL RESOURCES
# ------------------------------------------------------------------------------

data "azurerm_client_config" "current" {}

# Puit de logs centralisé TB-Groupe
data "azurerm_log_analytics_workspace" "central_logs" {
  provider            = azurerm.management
  name                = "log-platform-logs-prod"
  resource_group_name = "rg-platform-logs-prod"
}

# ------------------------------------------------------------------------------
# RESSOURCES PRINCIPALES
# ------------------------------------------------------------------------------

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}-${var.project_code}-${var.environment}"
  location = var.location
  tags     = var.tags
}

# Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = "st${var.prefix}veille${var.environment}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  # Activation de l'hébergement de site web statique pour dashboard.html
  static_website {
    index_document     = "dashboard.html"
    error_404_document = "404.html"
  }

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "POST", "OPTIONS"]
      allowed_origins    = ["*"] # A restreindre en production vers l'URL finale
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  tags = var.tags
}

# Service Plan (Premium V2 strict pour l'audit sémantique CamemBERT)
resource "azurerm_service_plan" "app_plan" {
  name                = "plan-${var.prefix}-${var.project_code}-${var.environment}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "EP1"
  tags                = var.tags
}

# Function App
resource "azurerm_linux_function_app" "function" {
  name                = "func-${var.prefix}-${var.project_code}-${var.environment}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  service_plan_id            = azurerm_service_plan.app_plan.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key

  site_config {
    application_stack {
      python_version = "3.10"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "WEBSITE_TIMEZONE"         = "Europe/Paris"
    "GEMINI_API_KEY"           = "@#{GEMINI_API_KEY}#@"
    "TAVILY_API_KEY"           = "@#{TAVILY_API_KEY}#@"
    "GOOGLE_JSON_CREDENTIALS"  = "@#{GOOGLE_JSON_CREDENTIALS}#@"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Key Vault
resource "azurerm_key_vault" "kv" {
  name                        = "kv-${var.prefix}-${var.project_code}-${var.environment}"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"

  tags = var.tags
}

# Permissions pour la Function (Accès au Key Vault)
resource "azurerm_key_vault_access_policy" "func_policy" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.function.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

# ------------------------------------------------------------------------------
# MLFLOW SERVER (ACI)
# ------------------------------------------------------------------------------

resource "azurerm_storage_container" "mlflow_artifacts" {
  name                  = "mlflow-artifacts"
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

resource "azurerm_container_group" "mlflow" {
  name                = "aci-${var.prefix}-${var.project_code}-mlf-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  ip_address_type     = "Public"
  os_type             = "Linux"

  container {
    name   = "mlflow-server"
    image  = "ghcr.io/mlflow/mlflow:v2.10.2"
    cpu    = "1"
    memory = "2"

    ports {
      port     = 5000
      protocol = "TCP"
    }

    commands = [
      "/bin/sh",
      "-c",
      "pip install azure-storage-blob && mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root wasbs://${azurerm_storage_container.mlflow_artifacts.name}@${azurerm_storage_account.storage.name}.blob.core.windows.net/ --host 0.0.0.0"
    ]

    environment_variables = {
      "AZURE_STORAGE_CONNECTION_STRING" = azurerm_storage_account.storage.primary_connection_string
    }
  }

  tags = var.tags
}

# ------------------------------------------------------------------------------
# MONITORING & DIAGNOSTICS (Standard TB-Groupe)
# ------------------------------------------------------------------------------

resource "azurerm_monitor_diagnostic_setting" "func_diag" {
  name                       = "diag-${azurerm_linux_function_app.function.name}"
  target_resource_id         = azurerm_linux_function_app.function.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.central_logs.id

  enabled_log {
    category = "FunctionAppLogs"
    retention_policy {
      enabled = false
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
    retention_policy {
      enabled = false
    }
  }
}

