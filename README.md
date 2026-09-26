# kubernetes-model-serving

A beginner-friendly Session 1 FastAPI service with health and placeholder generation endpoints. All Python dependencies run inside Docker; no host Python setup is required.

## Build and run

Build the image from the project directory:

```sh
docker build -t model-serving-api .
```

Start the container and publish the API on port 8000:

```sh
docker run --name model-serving-api -d -p 8000:8000 model-serving-api
```

Open the interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

## Try the API

Check service health:

```sh
curl -i http://localhost:8000/health
```

Send a generation request:

```sh
curl -i -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Hello, model!","max_new_tokens":32}'
```

FastAPI returns HTTP 422 for invalid input, such as an empty prompt:

```sh
curl -i -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"","max_new_tokens":32}'
```

View request logs. Generation logs contain only the prompt length and token limit, not the prompt text:

```sh
docker logs model-serving-api
```

## Cleanup

Stop and remove the container:

```sh
docker stop model-serving-api
docker rm model-serving-api
```
