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
        source_content_type = head.get('ContentType', 'binary/octet-stream')
        
        is_synced = False
        if metadata.get('is_replicated') in ['true', 'True'] or metadata.get('x-amz-meta-is_replicated') in ['true', 'True']:
            is_synced = True
            
        if is_synced:
            replicated_key = metadata.get('replicated_key') or metadata.get('x-amz-meta-replicated_key')
            
            # If the replicated_key exactly matches the current path, it's a cross-bucket sync. Skip.
            if replicated_key == key:
                print(f"Skipping {key}: detected replication flag and paths match.")
                return
            
            # If they don't match, OR if replicated_key is missing entirely, it's a local move/rename. Replicate.
            print(f"Path mismatch or legacy file detected for {key}. Proceeding with replication.")

    except Exception as e:
        print(f"Error checking metadata for {key}: {e}")
        return

    # 2. PERFORM COPY WITH CONTENT-TYPE & NEW METADATA
    copy_source = {'Bucket': source_bucket, 'Key': key}
    
    print(f"Copying {key} from bucket {source_bucket} to bucket {target_bucket}...")
    try:
        s3.copy_object(
            Bucket=target_bucket, 
            Key=key, 
            CopySource=copy_source,
            Metadata={
                'is_replicated': 'true',
                'replicated_key': key  # <--- Store the exact path we are replicating to
            },
            MetadataDirective='REPLACE',
            ContentType=source_content_type
        )
    except Exception as e:
        print(f'[Error] Copying {key} failed: {e}')
    else:
        print(f'[OK] Copied the {key} key successfully')
