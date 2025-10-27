# Photo Upload App

This repository (and the accompanying blog post at  
https://devbuildit.com/2025/10/27/photo-upload-app/) shows you how to set up a simple, photo-upload application that uploads images to an s3 bucket. It uses:

- **Terraform** to provision an S3 bucket, IAM roles, and Cognito User & Identity Pools (with hosted UI)  
- A local **Streamlit** app to handle OAuth2 “authorization code” flow, exchange JWTs for AWS credentials, and upload/list each user’s photos under their own S3 prefix


# Installation  

Installation is based on two parts:
- AWS components deployed using Terraform.
- Locally running Streamlit Python application 

## Requirements: ##
- AWS Account
- Terraform CLI installed with access to your target AWS account (via temporary Indentity centre credentials or AWS IAM access keys)
- Python 3.12+


## Deployment (Terraform)
- Clone repo into a source folder
- Navigate into tf subdirectory
- Consider changing application defaults set in terraform.tfvars
- Run command 'Terraform init'
- Run command 'Terraform plan'
- Run command 'Terraform apply' (approve when prompted)
- Note Terraform output values for Streamlit deployment
- Log into AWS console and obtain user pool client secret (Cognito - > user pools -> photo-upload-user-pool -> app clients -> photo-upload-client)

## Deployment (Streamlit)
- Update config/.env with values from Terrafrom deployment
- move into project top folder
- run python3 -m venv .venv
- run source .venv/bin/activate
- run pip install -r requirements.txt
- navigate into app folder
- run streamlit run main.py
- open browser to http://localhost:8501


## Removal (AWS Components)
- Empty contents of S3 photo-upload bucket
- Run command 'Terraform destroy'