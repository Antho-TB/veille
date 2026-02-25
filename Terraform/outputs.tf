output "function_app_name" {
  value       = azurerm_linux_function_app.function.name
  description = "Le nom de l'application Function Azure déployée"
}

output "function_app_default_hostname" {
  value       = azurerm_linux_function_app.function.default_hostname
  description = "L'URL par défaut de l'application Function Azure"
}

output "key_vault_uri" {
  value       = azurerm_key_vault.kv.vault_uri
  description = "L'URI du Key Vault Azure"
}
