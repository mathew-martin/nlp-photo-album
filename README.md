# Photo Album (AWS)

An S3/OpenSearch/Lex powered photo album with natural-language search, automatic indexing via Rekognition, a static S3-hosted frontend, and CI/CD through CodePipeline/CodeBuild.

## Stack
- Storage: S3 bucket `cc-hw3-b2-photos` (public read for image display)
- Indexing Lambda (LF1): `cc-hw3-lf1-index-photos`
  - Trigger: S3 PUT on `cc-hw3-b2-photos`
  - Actions: Rekognition `detect_labels`, read custom labels from `x-amz-meta-customLabels`, merge/dedupe, index into OpenSearch `photos`
- Search Lambda (LF2): `cc-hw3-lf2-search-photos`
  - Supports Lex V2 (bot id `PIFZCZXUFU`, alias `YCK6WUL81O`, locale `en_US`); falls back to simple keyword split
  - `q="*"` returns all docs; result size up to 100
- OpenSearch: domain `photos`, index `photos`
- Lex V2 bot: `cc-hw3-photo-search` (SearchIntent with Keywords slot)
- API Gateway (EDGE, stage `prod`): `https://3unsm2lg6i.execute-api.us-east-1.amazonaws.com/prod`
  - GET `/search?q=<query>` → LF2 (API key required)
  - PUT `/photos?objectKey=<key>` → S3 proxy to `cc-hw3-b2-photos` (API key required; optional `x-amz-meta-customLabels`)
  - CORS enabled for `/search` and `/photos`
- Frontend: S3 static site `cc-hw3-b1-frontend`
  - URL: `http://cc-hw3-b1-frontend.s3-website-us-east-1.amazonaws.com`
  - Config file: `frontend/config.js` (copy from `config.example.js`)
- CI/CD (CodePipeline/CodeBuild):
  - Artifact bucket: `nlp-photo-album-codepipeline-artifacts`
  - Pipelines: `nlp-photo-album-backend-pipeline` (deploys LF1/LF2), `nlp-photo-album-frontend-pipeline` (syncs frontend to B1)
  - Buildspecs: `buildspec-backend.yml`, `buildspec-frontend.yml`

## Pipeline troubleshooting (what went wrong and the fixes)
- Both backend and frontend CodeBuild projects were failing in `DOWNLOAD_SOURCE` with `authorization failed for primary source` because the CodeBuild roles lacked permission to use the GitHub CodeStar connection. Fix: add an inline policy granting `codestar-connections:UseConnection` on `arn:aws:codeconnections:us-east-1:217522444053:connection/b8e76c7f-11c6-46e7-9baa-bd33e49b575d` to:
  - Backend role: `nlp-photo-album-codebuild-backend-role`
  - Frontend role: `nlp-photo-album-codebuild-frontend-role`
- Backend POST_BUILD then failed because multiline `aws lambda update-function-code` commands were mis-parsed and dropped `--function-name`. Fix: flatten the two Lambda update commands to single lines in `buildspec-backend.yml`.
- Both CodeBuild projects are configured to read `buildspec-backend.yml` / `buildspec-frontend.yml` from the repo. After the above fixes, pipelines run successfully (backend deploys LF1/LF2, frontend syncs to the S3 static site bucket).

## Repo layout
- `lambdas/index-photos/lambda_function.py` — LF1 handler
- `lambdas/search-photos/lambda_search.py` — LF2 handler
- `frontend/` — static site (HTML/CSS/JS + config.example.js)
- `buildspec-backend.yml` — zips Lambdas and updates LF1/LF2
- `buildspec-frontend.yml` — syncs `frontend/` to the frontend bucket

## Frontend usage
1) Create `frontend/config.js`:
   ```js
   window.CONFIG = {
     API_BASE: "https://3unsm2lg6i.execute-api.us-east-1.amazonaws.com/prod",
     API_KEY: "<your api key>"
   };
   ```
2) Deploy: `aws s3 sync frontend/ s3://cc-hw3-b1-frontend/ --delete --region us-east-1`
3) Browse: `http://cc-hw3-b1-frontend.s3-website-us-east-1.amazonaws.com`
   - Search bar at top; clear search → shows all photos (`*`)
   - Click images for lightbox with next/prev arrows
   - “+” opens upload modal (optional custom labels); Rekognition auto-labels

## Backend notes
- LF1 env: hardcoded `us-east-1`; uses OPENSEARCH_ENDPOINT in code.
- LF2 env: `OPENSEARCH_ENDPOINT`, `INDEX`, `LEX_BOT_ID`, `LEX_BOT_ALIAS_ID`, `LEX_LOCALE`; `q="*"` → match_all.
- IAM: ensure LF1 has S3 GetObject/HeadObject, Rekognition, and OpenSearch HTTP; LF2 has OpenSearch HTTP (and Lex RecognizeText).

## Pipelines (main branch)
- Source: CodeStar connection `arn:aws:codeconnections:us-east-1:217522444053:connection/b8e76c7f-11c6-46e7-9baa-bd33e49b575d`
- Backend CodeBuild: `nlp-photo-album-backend-build` (role `nlp-photo-album-codebuild-backend-role`)
- Frontend CodeBuild: `nlp-photo-album-frontend-build` (role `nlp-photo-album-codebuild-frontend-role`)
- Runs on push to `main` and deploys automatically.

## API quick test
```bash
API=https://3unsm2lg6i.execute-api.us-east-1.amazonaws.com/prod
KEY=<api key>
curl -H "x-api-key: $KEY" -G "$API/search" --data-urlencode "q=cat"
```

## Upload quick test (no custom labels)
```bash
OBJ=test-$(date +%s).jpg
curl -H "x-api-key: $KEY" -H "Content-Type: image/jpeg" \
  -X PUT "$API/photos?objectKey=$OBJ" --data-binary @path/to/file.jpg
```
