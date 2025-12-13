# 1. Архівуємо код Python для Ламбди
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "../lambda/lambda_function.py"
  output_path = "../lambda/payload.zip"
}

# 2. Створюємо роль (дозвіл Ламбді писати в S3)
resource "aws_iam_role" "lambda_role" {
  name = "agri_lambda_receiver_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Даємо цій ролі права на твій бакет
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "lambda_s3_write"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow",
      Action = ["s3:PutObject"],
      Resource = "${aws_s3_bucket.agri_data.arn}/*"
    }]
  })
}

# 3. Сама Ламбда Функція
resource "aws_lambda_function" "sensor_receiver" {
  filename         = "../lambda/payload.zip"
  function_name    = "HarvestGuardReceiver"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.agri_data.bucket
    }
  }
}

# 4. Публічна URL адреса (щоб ESP32 міг достукатися)
resource "aws_lambda_function_url" "receiver_url" {
  function_name      = aws_lambda_function.sensor_receiver.function_name
  authorization_type = "NONE" # Публічний доступ (для прототипу це ОК)
}

# Виводимо URL на екран після деплою
output "lambda_url" {
  value = aws_lambda_function_url.receiver_url.function_url
}