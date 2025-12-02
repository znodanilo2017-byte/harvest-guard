terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "eu-central-1"
}

# --- 1. STORAGE (S3) ---
resource "aws_s3_bucket" "agri_data" {
  bucket = "harvest-guard-lviv-2025" # Must match your Python script
  tags = { Name = "Harvest Guard Data Lake" }
}

# --- 2. REGISTRY (ECR) ---
resource "aws_ecr_repository" "agri_repo" {
  name = "harvest-guard-bot"
}

# --- 3. SECURITY (IAM ROLE) ---
resource "aws_iam_role" "agri_role" {
  name = "agri_sensor_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Allow access to S3 and ECR (to pull images)
resource "aws_iam_role_policy" "agri_policy" {
  name = "agri_access_policy"
  role = aws_iam_role.agri_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Action = ["s3:PutObject", "s3:ListBucket"],
        Resource = [aws_s3_bucket.agri_data.arn, "${aws_s3_bucket.agri_data.arn}/*"]
      },
      {
        Effect = "Allow",
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "agri_profile" {
  name = "agri_sensor_profile"
  role = aws_iam_role.agri_role.name
}

# --- 4. COMPUTE (EC2) ---
resource "aws_security_group" "agri_sg" {
  name        = "agri_ssh_access"
  description = "Allow SSH"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
  owners = ["099720109477"]
}

resource "aws_instance" "agri_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro" # Free tier
  key_name      = "my-aws-key" # <--- ENSURE THIS KEY EXISTS IN AWS
  
  vpc_security_group_ids = [aws_security_group.agri_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.agri_profile.name

  tags = { Name = "Harvest-Guard-Sensor-Node" }

  # Auto-install Docker on startup
  user_data = <<-EOF
              #!/bin/bash
              apt-get update -y
              apt-get install -y docker.io awscli
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ubuntu
              EOF
}