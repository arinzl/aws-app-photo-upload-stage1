import streamlit as st
import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime
from PIL import Image
import io
from auth import CognitoAuth
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from config/.env
config_path = os.path.join(os.path.dirname(__file__), '../config/.env')
load_dotenv(config_path)

# Configure logging to see errors in console and file
log_file = os.path.join(os.path.dirname(__file__), '../app_errors.log')
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode='a')
    ]
)

# Configure page
st.set_page_config(
    page_title="Photo Upload App",
    page_icon="📸",
    layout="wide"
)

# Initialize authentication
auth = CognitoAuth()

def upload_to_s3(file_obj, bucket_name, object_key, credentials):
    """Upload file to S3 using temporary credentials"""
    try:
        st.write(f"Debug: Uploading to bucket {bucket_name}, key {object_key}")
        st.write(f"Debug: Using region {os.getenv('AWS_REGION', 'us-east-1')}")

        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

        s3_client.upload_fileobj(file_obj, bucket_name, object_key)
        st.success(f"Successfully uploaded {object_key}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        error_text = f"AWS Error ({error_code}): {error_message}"
        st.error(error_text)
        st.error(f"Full error: {str(e)}")
        logging.error(f"UPLOAD ERROR: {error_text}")
        logging.error(f"FULL ERROR: {str(e)}")
        return False
    except Exception as e:
        error_text = f"Unexpected error: {str(e)}"
        st.error(error_text)
        logging.error(f"UPLOAD ERROR: {error_text}")
        return False

def list_user_photos(bucket_name, user_prefix, credentials):
    """List user's photos from S3"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=user_prefix
        )

        return response.get('Contents', [])
    except ClientError as e:
        st.error(f"Error listing files: {e}")
        return []

def main():
    st.title("📸 Photo Upload App")

    # Create an error container at the top that persists
    error_container = st.container()

    # Check authentication
    if not auth.is_authenticated():
        st.info("Please log in to upload and view your photos.")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", type="primary"):
                auth.login()

        with col2:
            if st.button("Register"):
                auth.register()

        return

    # User is authenticated
    user_info = auth.get_user_info()
    st.success(f"Welcome, {user_info.get('email', 'User')}!")

    # Logout button in sidebar
    with st.sidebar:
        st.write(f"Logged in as: {user_info.get('email', 'User')}")
        if st.button("Logout"):
            auth.logout()
            st.rerun()

    # Get AWS credentials
    credentials = auth.get_aws_credentials()
    if not credentials:
        st.error("Unable to get AWS credentials. Please try logging in again.")
        st.error("Debug: Check that your Cognito Identity Pool is properly configured")
        return
    else:
        st.write("Debug: Successfully obtained AWS credentials")
        st.write(f"Debug: AccessKeyId starts with: {credentials['AccessKeyId'][:10]}...")


    bucket_name = os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        st.error("S3 bucket name not configured.")
        return

    user_id = auth.get_user_id()
    user_prefix = f"users/{user_id}/"

    # Create tabs
    upload_tab, gallery_tab = st.tabs(["Upload Photos", "My Gallery"])

    with upload_tab:
        st.header("Upload New Photos")

        uploaded_files = st.file_uploader(
            "Choose photo files",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.write(f"Selected {len(uploaded_files)} file(s)")

            if st.button("Upload Photos", type="primary"):
                progress_bar = st.progress(0)
                success_count = 0

                for i, uploaded_file in enumerate(uploaded_files):
                    # Create unique filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{uploaded_file.name}"
                    object_key = f"{user_prefix}{filename}"

                    # Reset file pointer
                    uploaded_file.seek(0)

                    if upload_to_s3(uploaded_file, bucket_name, object_key, credentials):
                        success_count += 1

                    # Update progress
                    progress_bar.progress((i + 1) / len(uploaded_files))

                if success_count == len(uploaded_files):
                    st.success(f"Successfully uploaded {success_count} photo(s)!")
                else:
                    st.warning(f"Uploaded {success_count} out of {len(uploaded_files)} photo(s)")

                # Refresh the page to show new photos
                st.rerun()

    with gallery_tab:
        st.header("My Photo Gallery")

        # List user's photos
        photos = list_user_photos(bucket_name, user_prefix, credentials)

        if not photos:
            st.info("No photos uploaded yet. Go to the Upload tab to add some!")
        else:
            st.write(f"You have {len(photos)} photo(s)")

            # Display photos in a grid
            cols = st.columns(3)

            for i, photo in enumerate(photos):
                with cols[i % 3]:
                    try:
                        # Get photo from S3
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=credentials['AccessKeyId'],
                            aws_secret_access_key=credentials['SecretKey'],
                            aws_session_token=credentials['SessionToken'],
                            region_name=os.getenv('AWS_REGION', 'us-east-1')
                        )

                        obj = s3_client.get_object(Bucket=bucket_name, Key=photo['Key'])
                        image_data = obj['Body'].read()

                        # Display image
                        image = Image.open(io.BytesIO(image_data))
                        st.image(image, caption=photo['Key'].split('/')[-1], use_container_width=True)

                        # Add download button
                        st.download_button(
                            label="Download",
                            data=image_data,
                            file_name=photo['Key'].split('/')[-1],
                            mime="image/jpeg"
                        )

                    except Exception as e:
                        st.error(f"Error loading image: {e}")

if __name__ == "__main__":
    main()