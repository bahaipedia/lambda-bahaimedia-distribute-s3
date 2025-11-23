# lambda-bahaimedia-distribute-s3
Distribute files to regional s3 buckets after getting an upload in any one bucket

This function copies files uploaded in one s3 region to all other s3 regions. It captures "All object create events" in a target 
s3 bucket. When the files are duplicated metadata like "x-amz-meta-is_replicated true" will be set, and we look for that to determine
if further replication should proceed. 

Note that each region where an origin bucket exists will also have a local copy of this lambda function and lambda-bahaimedia-delete-s3.

s3 buckets have event notifications tied to Amazon SNS which goes like this:
  1. Event copyReplication or event deleteReplication triggers SNS topic
  2. SNS topic has 1 subscription per region where files are going to be copied whose endpoint is this function or lambda-bahaimedia-delete-s3

Eg, on the US server in an SNS subscription for the distribute function, the endpoints are:
  1. Region 1 distribute lambda
  2. Region 2 distribute lambda
  3. Region 3 distribute lambda

Note: If you ever want to run a sync command between buckets where most items do NOT have x-amz-meta-is_replicated true already set, it will be 
expensive as the files will be needlessly duplicated while that metadata is set everywhere. If you need to run that command in each bucket under
"Event notifications" find "copyReplication" and change it from "All object create events" to "Put" temporarily.
