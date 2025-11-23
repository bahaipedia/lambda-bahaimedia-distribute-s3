import urllib
import boto3
import ast
import json

print('Loading function')

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    sns_message = ast.literal_eval(event['Records'][0]['Sns']['Message'])
    target_bucket = context.function_name
    source_bucket = str(sns_message['Records'][0]['s3']['bucket']['name'])
    key = str(urllib.parse.unquote_plus(sns_message['Records'][0]['s3']['object']['key']))
    
    # 1. LOOP PREVENTION & METADATA RETRIEVAL
    try:
        head = s3.head_object(Bucket=source_bucket, Key=key)
        metadata = head.get('Metadata', {})
        source_content_type = head.get('ContentType', 'binary/octet-stream') # <--- Capture Content-Type
        
        # Debugging
        # print(f"Metadata found for {key}: {json.dumps(metadata)}")

        # Check for the tag in every possible format
        is_synced = False
        if metadata.get('is_replicated') in ['true', 'True']:
            is_synced = True
        if metadata.get('x-amz-meta-is_replicated') in ['true', 'True']:
            is_synced = True
            
        if is_synced:
            print(f"Skipping {key}: detected replication flag.")
            return

    except Exception as e:
        print(f"Error checking metadata for {key}: {e}")
        return

    # 2. PERFORM COPY WITH CONTENT-TYPE PRESERVATION
    copy_source = {'Bucket': source_bucket, 'Key': key}
    
    print(f"Copying {key} from bucket {source_bucket} to bucket {target_bucket}...")
    try:
        s3.copy_object(
            Bucket=target_bucket, 
            Key=key, 
            CopySource=copy_source,
            Metadata={'is_replicated': 'true'},
            MetadataDirective='REPLACE',
            ContentType=source_content_type  # <--- Re-apply the original Content-Type
        )
    except Exception as e:
        print(f'[Error] Copying {key} failed: {e}')
    else:
        print(f'[OK] Copied the {key} key successfully')
