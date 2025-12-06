import json
import os
import uuid

# test to see if pipeline works @ 1:44am

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

REGION = os.getenv("AWS_REGION", "us-east-1")
SERVICE = "es"
OPENSEARCH_ENDPOINT = os.getenv("OPENSEARCH_ENDPOINT")
INDEX = os.getenv("INDEX", "photos")
LEX_BOT_ID = os.getenv("LEX_BOT_ID")
LEX_BOT_ALIAS_ID = os.getenv("LEX_BOT_ALIAS_ID")
LEX_LOCALE = os.getenv("LEX_LOCALE", "en_US")

session = boto3.Session()
credentials = session.get_credentials()
lex = boto3.client("lexv2-runtime", region_name=REGION)


def search_opensearch(keywords):
    if keywords:
        must_clauses = [{"match": {"labels": kw}} for kw in keywords]
        query = {"query": {"bool": {"must": must_clauses}}}
    else:
        query = {"query": {"match_all": {}}}

    url = f"https://{OPENSEARCH_ENDPOINT}/{INDEX}/_search"
    request = AWSRequest(
        method="GET",
        url=f"{url}?size=100",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, SERVICE, REGION).add_auth(request)

    http = session._session.create_client(
        service_name="es",
        region_name=REGION,
        endpoint_url=f"https://{OPENSEARCH_ENDPOINT}",
    )._endpoint.http_session

    response = http.send(request.prepare())
    body = response.text
    if response.status_code != 200:
        raise RuntimeError(f"OpenSearch error {response.status_code}: {body}")
    return json.loads(body)


def extract_keywords_with_lex(query_text):
    if not LEX_BOT_ID or not LEX_BOT_ALIAS_ID:
        return None
    try:
        resp = lex.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId=LEX_LOCALE,
            sessionId=str(uuid.uuid4()),
            text=query_text,
        )
        slots = resp.get("sessionState", {}).get("intent", {}).get("slots", {}) or {}
        keywords = []
        for slot in slots.values():
            if not slot:
                continue
            value = slot.get("value", {}).get("interpretedValue")
            if value:
                keywords.extend(
                    [w.strip() for w in value.replace(" and ", ",").split(",") if w.strip()]
                )
        return keywords or None
    except Exception as e:
        print(f"Lex error: {e}")
        return None


def fallback_keywords(query_text):
    parts = [p.strip() for p in query_text.replace(" and ", ",").split(",")]
    keywords = []
    for part in parts:
        if part:
            keywords.extend(part.split())
    seen = set()
    ordered = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            ordered.append(kw)
    return ordered


def lambda_handler(event, context):
    print("Event:", event)

    q_params = event.get("queryStringParameters") or {}
    query_text = q_params.get("q") if isinstance(q_params, dict) else None

    if not query_text:
        return {"statusCode": 400, "body": json.dumps({"message": "Missing query param q"})}

    if query_text.strip() == "*":
        keywords = []
    else:
        keywords = extract_keywords_with_lex(query_text) or fallback_keywords(query_text)
    print(f"Keywords: {keywords}")

    os_resp = search_opensearch(keywords)
    hits = os_resp.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        source = hit.get("_source", {})
        results.append(
            {
                "objectKey": source.get("objectKey"),
                "bucket": source.get("bucket"),
                "labels": source.get("labels", []),
                "createdTimestamp": source.get("createdTimestamp"),
            }
        )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"results": results}),
    }
