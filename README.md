# kubernetes-model-serving

A CPU-only FastAPI model server that loads `Qwen/Qwen2.5-0.5B-Instruct` once and serves real text generation. Python dependencies stay inside Docker; no host Python setup is required.

## Build and test

Build the test target and run the mocked API contract tests. Tests do not download Qwen.

```sh
docker build --target test -t model-serving-api-test .
docker run --rm model-serving-api-test
```

Build the runtime image:

```sh
docker build -t model-serving-api .
```

## Run

Start one Uvicorn worker and mount a named volume for the Hugging Face cache:

```sh
docker run --rm \
  --name model-serving-api \
  -p 8000:8000 \
  -v hf-cache:/models/cache \
  model-serving-api
```

The first start automatically downloads approximately 1 GB of model files into `hf-cache`. Wait for the `model_load_complete` log line before sending requests. Later containers that mount the same volume reuse those files, although they must still load the model into memory.

Open the interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

## Call the API

Health check:

```sh
curl -s http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Real generation request:

```sh
curl -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain Kubernetes in one sentence.","max_new_tokens":32}'
```

The generated wording can vary, but the response contains non-empty `text` and the model name:

```json
{
  "text": "Kubernetes is an open-source platform...",
  "model": "Qwen/Qwen2.5-0.5B-Instruct"
}
```

Invalid request—returns HTTP 422 before inference:

```sh
curl -i -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Hello","max_new_tokens":0}'
```

A structurally valid request that exceeds `MAX_INPUT_TOKENS` after chat-template tokenization returns HTTP 413.

## Configuration

The container accepts these environment variables:

| Variable | Default |
| --- | --- |
| `MODEL_ID` | `Qwen/Qwen2.5-0.5B-Instruct` |
| `MAX_INPUT_TOKENS` | `512` |
| `DEFAULT_MAX_NEW_TOKENS` | `32` |
| `MAX_NEW_TOKENS` | `128` |
| `HF_HOME` | `/models/cache` |

For example:

```sh
docker run --rm \
  --name model-serving-api \
  -p 8000:8000 \
  -v hf-cache:/models/cache \
  -e DEFAULT_MAX_NEW_TOKENS=16 \
  model-serving-api
```

## Logs and timing

In another terminal, follow startup and request logs:

```sh
docker logs -f model-serving-api
```

Logs include model load duration, input token count, output-token limit, and request latency. They do not include prompts or generated text.

After startup completes, time two identical warm requests separately:

```sh
time curl -s -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain Kubernetes briefly.","max_new_tokens":32}'

time curl -s -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain Kubernetes briefly.","max_new_tokens":32}'
```

## Inspect the model cache

`hf-cache` is Docker-managed disk storage, not a directory in this repository. A Docker volume outlives the containers that mount it.

List the volume:

```sh
docker volume ls --filter name=hf-cache
```

Inspect its contents and size without installing host tools:

```sh
docker run --rm \
  -v hf-cache:/models/cache:ro \
  alpine sh -c 'du -sh /models/cache && find /models/cache -maxdepth 2 -type d'
```

## Stop and clean up

When the container was started with `--rm`, stopping it also removes it:

```sh
docker stop model-serving-api
```

If it was started without `--rm`, remove it separately:

```sh
docker rm model-serving-api
```

Removing the container does not remove the model files. Full cleanup deletes the volume and both images:

```sh
docker volume rm hf-cache
docker rmi model-serving-api model-serving-api-test
```

Confirm the cache volume is gone; no output means it was removed:

```sh
docker volume ls --filter name=hf-cache
```

If Docker reports that the volume is in use, find and remove the leftover container first:

```sh
docker ps -a --filter volume=hf-cache
docker rm -f <container_id_or_name>
docker volume rm hf-cache
```
