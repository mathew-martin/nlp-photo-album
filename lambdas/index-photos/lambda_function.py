import json
import boto3
import urllib.parse
from datetime import datetime

# test to see if pipeline works @ 1:58am

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

region = "us-east-1"
service = "es"

credentials = boto3.Session().get_credentials()

rekognition = boto3.client("rekognition")
s3 = boto3.client("s3")

# ------------ CHANGE THIS ------------
OPENSEARCH_ENDPOINT = "search-photos-rjpsl5liewh6itrngz2eput4am.us-east-1.es.amazonaws.com"
INDEX = "photos"
# ------------------------------------


def send_to_opensearch(document):
    url = f"https://{OPENSEARCH_ENDPOINT}/{INDEX}/_doc"

    request = AWSRequest(
        method="POST",
        url=url,
        data=json.dumps(document),
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, service, region).add_auth(request)

    session = boto3.session.Session()
    http = session._session.create_client(
        service_name="es",
        region_name=region,
        endpoint_url=f"https://{OPENSEARCH_ENDPOINT}",
    )._endpoint.http_session

    response = http.send(request.prepare())
    return response.status_code, response.text


def get_custom_labels(bucket, key):
    """Read custom labels from S3 object metadata (x-amz-meta-customLabels)."""
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        metadata = head.get("Metadata", {}) or {}
        raw = metadata.get("customlabels") or metadata.get("customLabels")
        if not raw:
            return []
        return [label.strip() for label in raw.split(",") if label.strip()]
    except Exception as e:
        print(f"Failed to read custom labels: {e}")
        return []


def lambda_handler(event, context):
    print("Event:", event)

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])

    custom_labels = get_custom_labels(bucket, key)
    print(f"Custom labels: {custom_labels}")

    rekog_resp = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=10,
    )

    detected_labels = [label["Name"] for label in rekog_resp["Labels"]]
    print(f"Rekognition labels: {detected_labels}")

    combined = []
    for label in custom_labels + detected_labels:
        if label not in combined:
            combined.append(label)

    document = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": datetime.utcnow().isoformat(),
        "labels": combined,
    }

    status, text = send_to_opensearch(document)
    print("OpenSearch response:", status, text)

    return {"statusCode": 200, "body": json.dumps("Done")}
