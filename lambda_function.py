import urllib.parse
import boto3
import json

print('Loading function')

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    # 1. FIX: Use json.loads instead of ast.literal_eval to prevent crashes on 'null' or booleans in the AWS event
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])
    
    target_bucket = context.function_name
    source_bucket = str(sns_message['Records'][0]['s3']['bucket']['name'])
    key = str(urllib.parse.unquote_plus(sns_message['Records'][0]['s3']['object']['key']))
    
    # 2. LOOP PREVENTION & METADATA RETRIEVAL
    try:
        head = s3.head_object(Bucket=source_bucket, Key=key)
        metadata = head.get('Metadata', {})
        source_content_type = head.get('ContentType', 'binary/octet-stream')
        
        is_synced = False
        if metadata.get('is_replicated') in ['true', 'True'] or metadata.get('x-amz-meta-is_replicated') in ['true', 'True']:
            is_synced = True
            
        if is_synced:
            raw_rep_key = metadata.get('replicated_key') or metadata.get('x-amz-meta-replicated_key')
            
            # Decode the key (handles None safely)
            replicated_key = urllib.parse.unquote_plus(raw_rep_key) if raw_rep_key else None
            
            # If the replicated_key exactly matches the current path, it's a cross-bucket sync. Skip.
            if replicated_key == key:
                print(f"Skipping {key}: detected replication flag and paths match.")
                return
            
            # If they don't match, OR if replicated_key is missing entirely, it's a local move/rename. Replicate.
            print(f"Path mismatch or legacy file detected for {key}. Proceeding with replication.")

    except Exception as e:
        print(f"Error checking metadata for {key}: {e}")
        return

    # 3. PERFORM COPY WITH CONTENT-TYPE & NEW METADATA
    copy_source = {'Bucket': source_bucket, 'Key': key}
    
    # Preserve existing metadata, just update our specific sync flags
    new_metadata = metadata.copy()
    new_metadata['is_replicated'] = 'true'
    new_metadata['replicated_key'] = urllib.parse.quote_plus(key)
    
    print(f"Copying {key} from bucket {source_bucket} to bucket {target_bucket}...")
    try:
        s3.copy_object(
            Bucket=target_bucket, 
            Key=key, 
            CopySource=copy_source,
            Metadata=new_metadata,
            MetadataDirective='REPLACE',
            ContentType=source_content_type
        )
    except Exception as e:
        print(f'[Error] Copying {key} failed: {e}')
    else:
        print(f'[OK] Copied the {key} key successfully')
