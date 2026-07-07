# AWS Console Setup Guide (ShopMart Pipeline)

This guide provides step-by-step instructions to set up the ShopMart Sales Data Pipeline on AWS using the AWS Management Console. All resources selected are compliant with the AWS Free Tier.

---

## Prerequisites
1. An AWS Account (New accounts receive 12 months of Free Tier services).
2. The AWS CLI installed locally (optional, but helpful for testing).
3. Python 3.11 installed locally (for packaging the Lambda zip).

---

## Step 1: Create Amazon S3 Buckets
We need three separate buckets: one for raw ingestion, one for processed clean Parquet files, and one for quarantined records.

1. Open the **Amazon S3 Console** (search "S3" in the AWS search bar).
2. Click **Create bucket**.
3. Configure the **Raw Bucket**:
   - **Bucket name:** `shopmart-raw-data-<your-name>` (must be globally unique).
   - **AWS Region:** Select your preferred region (e.g., `us-east-1`).
   - Leave other settings as default and click **Create bucket**.
4. Repeat the process to create:
   - **Processed Bucket:** `shopmart-processed-data-<your-name>`
   - **Quarantine Bucket:** `shopmart-quarantine-data-<your-name>`

---

## Step 2: Create Amazon DynamoDB Table
The metadata database checks for duplicate uploads and logs process success.

1. Open the **DynamoDB Console**.
2. Click **Create table**.
3. Configure Table parameters:
   - **Table name:** `shopmart-metadata`
   - **Partition key:** `file_name` (type: **String**).
   - **Table class:** DynamoDB Standard.
   - **Capacity calculator / Settings:** Choose **Default settings** (or select **Provisioned** capacity and set Read/Write units to 5 to guarantee it remains free tier).
4. Click **Create table**.

---

## Step 3: Create Amazon SNS Alert Topic
This topic sends emails to operators when invalid data or system failures occur.

1. Open the **Amazon SNS Console**.
2. Click **Topics** on the left menu, then click **Create topic**.
3. Configure the Topic:
   - **Type:** Select **Standard**.
   - **Name:** `shopmart-pipeline-alerts`
   - Click **Create topic**.
4. After creation, copy the **ARN** (looks like `arn:aws:sns:us-east-1:123456789012:shopmart-pipeline-alerts`).
5. **Create Email Subscription:**
   - Under the created topic, click **Create subscription**.
   - **Protocol:** Select **Email**.
   - **Endpoint:** Enter your email address.
   - Click **Create subscription**.
   - *Note: Open your email inbox and click the "Confirm Subscription" link sent by AWS.*

---

## Step 4: Create IAM Policy & Execution Role
Lambda needs permissions to read/write from S3, write to DynamoDB, send logs to CloudWatch, and publish to SNS.

1. Open the **IAM Console**.
2. **Create Policy:**
   - Click **Policies** on the left side, then click **Create policy**.
   - Click the **JSON** tab and paste the following policy (replace `<your-name>` and account ID `123456789012` with your actual bucket names and account number):
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "logs:CreateLogGroup",
             "logs:CreateLogStream",
             "logs:PutLogEvents"
           ],
           "Resource": "arn:aws:logs:*:*:*"
         },
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject",
             "s3:ListBucket"
           ],
           "Resource": [
             "arn:aws:s3:::shopmart-raw-data-<your-name>",
             "arn:aws:s3:::shopmart-raw-data-<your-name>/*"
           ]
         },
         {
           "Effect": "Allow",
           "Action": [
             "s3:PutObject"
           ],
           "Resource": [
             "arn:aws:s3:::shopmart-processed-data-<your-name>/*",
             "arn:aws:s3:::shopmart-quarantine-data-<your-name>/*"
           ]
         },
         {
           "Effect": "Allow",
           "Action": [
             "dynamodb:PutItem",
             "dynamodb:GetItem",
             "dynamodb:UpdateItem"
           ],
           "Resource": "arn:aws:dynamodb:*:*:table/shopmart-metadata"
         },
         {
           "Effect": "Allow",
           "Action": [
             "sns:Publish"
           ],
           "Resource": "arn:aws:sns:*:*:shopmart-pipeline-alerts"
         }
       ]
     }
     ```
   - Click **Next: Tags**, then **Next: Review**.
   - **Name:** `ShopMartPipelinePolicy`
   - Click **Create policy**.
3. **Create Role:**
   - Click **Roles** on the left side, then click **Create role**.
   - **Trusted entity type:** Select **AWS service**.
   - **Use case:** Select **Lambda** from the dropdown list. Click **Next**.
   - **Attach permissions:** Search for `ShopMartPipelinePolicy`, select it, and click **Next**.
   - **Role name:** `ShopMartLambdaRole`
   - Click **Create role**.

---

## Step 5: Package & Deploy AWS Lambda
Because our pipeline uses `pandas` and `pyarrow`, we need to package our python code with dependencies or attach an AWS Lambda Layer containing Pandas.
*Tip: To keep manual deployment simple, we will use AWS's built-in **AWSSDKPandas** Lambda Layer.*

1. Open the **AWS Lambda Console**.
2. Click **Create function**.
3. Configure the function:
   - Select **Author from scratch**.
   - **Function name:** `shopmart-data-processor`
   - **Runtime:** Select **Python 3.11** (matches our dependencies).
   - **Change default execution role:** Choose **Use an existing role**, and select `ShopMartLambdaRole`.
   - Click **Create function**.
4. **Attach Pandas Layer:**
   - On the function details page, scroll down to the bottom and locate the **Layers** section.
   - Click **Add a layer**.
   - Select **AWS layers**.
   - Under the AWS layer dropdown, choose **AWSSDKPandas-Python311** (a pre-configured AWS layer containing Pandas, PyArrow, and fsspec).
   - **Version:** Select the latest version (e.g. version 2 or 3).
   - Click **Add**.
5. **Upload Code:**
   - Under the **Code** tab, copy the contents of `src/pipeline.py` and overwrite the default template in `lambda_function.py`.
   - Alternatively, change the handler endpoint config. (Under **Runtime settings**, ensure handler is configured as `lambda_function.lambda_handler`).
   - Click **Deploy**.
6. **Set Environment Variables:**
   - Go to the **Configuration** tab, then select **Environment variables** on the left.
   - Click **Edit** and add the following keys:
     - `PROCESSED_BUCKET_NAME`: `shopmart-processed-data-<your-name>`
     - `QUARANTINE_BUCKET_NAME`: `shopmart-quarantine-data-<your-name>`
     - `METADATA_TABLE_NAME`: `shopmart-metadata`
     - `SNS_TOPIC_ARN`: Paste your SNS ARN from Step 3.
   - Click **Save**.
7. **Increase Timeout:**
   - Go to **Configuration** -> **General configuration**. Click **Edit**.
   - Set **Timeout** to `2 minutes` (to avoid timeout on larger files).
   - Set **Memory** to `512 MB`.
   - Click **Save**.

---

## Step 6: Create S3 Event Trigger
We want the Lambda to trigger automatically whenever a CSV file lands in S3.

1. In the Lambda console under **Function overview**, click **Add trigger**.
2. **Select a source:** Choose **S3**.
3. Configure the trigger:
   - **Bucket:** `shopmart-raw-data-<your-name>`
   - **Event type:** `All object create events` (or `PUT`).
   - **Suffix:** `.csv`
   - Check the **Recursive loop recursive validation acknowledgment** box.
   - Click **Add**.

---

## Step 7: Test the Setup Hands-on
Now you can perform end-to-end testing of your pipeline.

1. **Verify Ingestion:**
   - Go to the S3 console, click `shopmart-raw-data-<your-name>`.
   - Click **Upload**, select the file `sample_sales_data.csv` (rename it to `store_01_20260707.csv` first), and click **Upload**.
2. **Verify Logs:**
   - Go to the Lambda console -> **Monitor** tab -> click **View CloudWatch logs**.
   - Check the newest Log Stream to verify that pandas ran, rows were validated, and data was saved.
3. **Verify S3 processed data:**
   - Open `shopmart-processed-data-<your-name>` S3 bucket. You should see a new folder path: `processed/year=2024/month=01/day=15/` containing a `.parquet` file.
4. **Verify DynamoDB:**
   - Open DynamoDB table `shopmart-metadata` -> click **Explore table items**. You should see the file logged with status `SUCCESS` along with its row counts and revenue aggregates.
