# IAM role for authenticated users
resource "aws_iam_role" "authenticated_role" {
  name = "${var.app_name}-authenticated-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.photo_upload_identity_pool.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })
}

# IAM policy for S3 access
resource "aws_iam_role_policy" "authenticated_s3_policy" {
  name = "${var.app_name}-s3-policy"
  role = aws_iam_role.authenticated_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.photo_uploads.arn}/users/$${cognito-identity.amazonaws.com:sub}/*",
          "${aws_s3_bucket.photo_uploads.arn}/users/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.photo_uploads.arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "users/$${cognito-identity.amazonaws.com:sub}/*",
              "users/*"
            ]
          }
        }
      }
    ]
  })
}