# S3 Bucket for photo uploads
resource "aws_s3_bucket" "photo_uploads" {
  bucket = "${var.app_name}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "photo_uploads_encryption" {
  bucket = aws_s3_bucket.photo_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "photo_uploads_pab" {
  bucket = aws_s3_bucket.photo_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}