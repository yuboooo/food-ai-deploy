import boto3
import os

def download_s3_bucket(bucket_name, local_dir):
    # Create an S3 client
    s3 = boto3.client('s3')

    paginator = s3.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket_name}
    
    for page in paginator.paginate(**operation_parameters):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                local_file_path = os.path.join(local_dir, key)

                # Create local directory structure if it doesn't exist
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                # Download the file
                print(f"Downloading {key} to {local_file_path}")
                s3.download_file(bucket_name, key, local_file_path)

if __name__ == "__main__":
    bucket_name = "food-ai-db" 
    local_dir = "../data/food_db_cloud/" 

    # Call the function
    download_s3_bucket(bucket_name, local_dir)
