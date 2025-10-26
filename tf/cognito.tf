# Cognito User Pool
resource "aws_cognito_user_pool" "photo_upload_pool" {
  name = coalesce(var.cognito_user_pool_name, "${var.app_name}-user-pool")

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  auto_verified_attributes = ["email"]

  username_attributes = ["email"]

  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true
    mutable            = true
  }
}

resource "aws_cognito_user_pool_client" "photo_upload_client" {
  name         = "${var.app_name}-client"
  user_pool_id = aws_cognito_user_pool.photo_upload_pool.id

  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  callback_urls                        = var.cognito_callback_urls
  logout_urls                          = var.cognito_logout_urls

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}

resource "aws_cognito_user_pool_domain" "photo_upload_domain" {
  domain       = "${var.app_name}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.photo_upload_pool.id
}

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "photo_upload_identity_pool" {
  identity_pool_name               = "${var.app_name}-identity-pool"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.photo_upload_client.id
    provider_name           = aws_cognito_user_pool.photo_upload_pool.endpoint
    server_side_token_check = false
  }
}

resource "aws_cognito_identity_pool_roles_attachment" "photo_upload_roles" {
  identity_pool_id = aws_cognito_identity_pool.photo_upload_identity_pool.id

  roles = {
    "authenticated" = aws_iam_role.authenticated_role.arn
  }
}