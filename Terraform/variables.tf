variable "location" {
  type        = string
  description = "Région Azure pour toutes les ressources"
  default     = "northeurope"
}

variable "prefix" {
  type        = string
  description = "Préfixe utilisé pour les ressources"
  default     = "shsv"
}

variable "project_code" {
  type        = string
  description = "Code du projet"
  default     = "veille"
}

variable "environment" {
  type        = string
  description = "Environnement (dev, prod)"
  default     = "prod"
}

variable "tags" {
  type        = map(string)
  description = "Tags obligatoires pour les ressources"
  default = {
    project    = "GDD-Veille"
    deployment = "IaC"
    project    = "GDD-Veille"
    deployment = "IaC"
  }
}

