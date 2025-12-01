# NLP Photo Album (AWS) – Lambdas

This directory contains the Lambda code for the assignment:

- `lambdas/index-photos/lambda_function.py`: Triggered by S3 PUT on the photos bucket. Uses Rekognition to detect labels, reads custom labels from `x-amz-meta-customlabels` (metadata key `customLabels`), merges/dedupes, and indexes the document into the OpenSearch `photos` index.
- `lambdas/search-photos/lambda_search.py`: Handles search requests (`q` query param). Optionally uses Lex V2 for keyword extraction (when configured), falls back to simple keyword splitting, queries OpenSearch, and returns matching photo metadata.

Environment/assumptions:
- Region hardcoded to `us-east-1` in the index Lambda. Search Lambda reads `AWS_REGION` (defaults to `us-east-1`).
- Search Lambda env vars: `OPENSEARCH_ENDPOINT`, `INDEX`, and (optionally) `LEX_BOT_ID`, `LEX_BOT_ALIAS_ID`, `LEX_LOCALE` for Lex V2 integration.
- Both Lambdas rely on AWS SDK in the Lambda runtime (no external deps).

Frontend (static)
- Location: `frontend/`
- Files: `index.html`, `style.css`, `app.js`, `config.example.js`
- Create `frontend/config.js` (copy from `config.example.js`) and set `API_BASE` and `API_KEY`.
- Upload the contents of `frontend/` to a static S3 site (public read) and point it at the API Gateway endpoints.

Deployment pointers:
- LF1 handler: `lambda_function.lambda_handler`
- LF2 handler: `lambda_search.lambda_handler`
- Ensure IAM roles allow: LF1 → S3 GetObject/HeadObject + Rekognition + ES HTTP; LF2 → ES HTTP; both → CloudWatch Logs.
