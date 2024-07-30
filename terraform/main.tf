/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.38.0"
    }
  }
}

variable "project_id" {
  type = string
}

variable "region" {
  default     = "asia-northeast1"
}

variable "fqdn" {
  type        = string
}

variable "lb_name" {
  default     = "iap-lb"
}

variable "iap_client_id" {
  type      = string
  sensitive = false
}

variable "iap_client_secret" {
  type      = string
  sensitive = true
}

variable "iap_user" {
    type = string
}

provider "google" {
  project = var.project_id
}

locals {
  enable_services = toset([
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "certificatemanager.googleapis.com",
    "artifactregistry.googleapis.com",
  ])
}

resource "google_project_service" "compute_service" {
  service = "compute.googleapis.com"
  disable_dependent_services = true
}

resource "google_project_service" "service" {
  for_each = local.enable_services
  project  = var.project_id
  service  = each.value
  timeouts {
    create = "60m"
    update = "120m"
  }
  depends_on = [
    google_project_service.compute_service
  ]
  disable_dependent_services = true
}

resource "google_vpc_access_connector" "connector" {
  name          = "vpc-connector"
  region        = var.region
  project       = var.project_id
  ip_cidr_range = "10.128.128.0/28"
  network       = "default"
  depends_on = [ google_project_service.service ]
}

resource "google_cloud_run_service" "chatapp" {
  name     = "chatapp"
  location = var.region
  project  = var.project_id

  metadata {
    annotations = {
      "run.googleapis.com/ingress" : "internal-and-cloud-load-balancing"
    }
  }
  template {
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" : google_vpc_access_connector.connector.name
      }
    }
    spec {
      containers {
        image = "gcr.io/cloudrun/hello"
      }
    }
  }
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  provider              = google
  name                  = "serverless-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_service.chatapp.name
  }
}

module "lb-http" {
  source  = "GoogleCloudPlatform/lb-http/google//modules/serverless_negs"

  project = var.project_id
  name    = var.lb_name

  ssl                             = true
  managed_ssl_certificate_domains = ["${var.fqdn}"]
  https_redirect                  = true

  backends = {
    default = {
      description = null
      groups = [
        {
          group = google_compute_region_network_endpoint_group.serverless_neg.id
        }
      ]
      enable_cdn             = false
      security_policy        = null
      custom_request_headers = null

      iap_config = {
        enable               = true
        oauth2_client_id     = var.iap_client_id
        oauth2_client_secret = var.iap_client_secret
      }
      log_config = {
        enable      = false
        sample_rate = null
      }
    }
  }
  depends_on = [ google_project_service.compute_service ]
}

data "google_iam_policy" "iap" {
  binding {
    role = "roles/iap.httpsResourceAccessor"
    members = [
      // "group:everyone@google.com", // a google group
      // "allAuthenticatedUsers"          // anyone with a Google account (not recommended)
      "user:${var.iap_user}"
    ]
  }
}

resource "google_iap_web_backend_service_iam_policy" "policy" {
  project             = var.project_id
  web_backend_service = "${var.lb_name}-backend-default"
  policy_data         = data.google_iam_policy.iap.policy_data
  depends_on = [
    module.lb-http
  ]
}

output "load-balancer-ip" {
  value = module.lb-http.external_ip
}

output "oauth2-redirect-uri" {
  value = "https://iap.googleapis.com/v1/oauth/clientIds/${var.iap_client_id}:handleRedirect"
}
