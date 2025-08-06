# AI Rate Limiter - Essential Testing Commands

## 🚀 Health Check
```bash
curl http://localhost:8501/health
```

## 📝 Complete Flow Testing

### 1. Create Queue with Rate Limiting
```bash
curl -X POST http://localhost:8501/api/v1/queue/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "test-queue",
    "providers": [
      {
        "provider_name": "OpenAI Provider",
        "provider_type": "openai",
        "api_key": "sk-your-openai-key",
        "limit": 10,
        "time_window": 60,
        "config": {
          "model": "gpt-3.5-turbo"
        }
      }
    ]
  }'
```

### 2. Create Worker for Queue
```bash
# Replace {queue_id} with the queue_id from step 1 response
curl -X POST http://localhost:8501/api/v1/worker/create/{queue_id} \
  -H "Content-Type: application/json" \
  -d '{
    "count": 2
  }'
```

### 3. Create Single Message
```bash
# Replace {queue_id} with the queue_id from step 1
curl -X POST http://localhost:8501/api/v1/message/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "{queue_id}",
    "prompt": "Hello, this is a test message",
    "system_prompt": "You are a helpful assistant"
  }'
```

### 4. Create Batch Messages
```bash
# Replace {queue_id} with the queue_id from step 1
curl -X POST http://localhost:8501/api/v1/message/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "{queue_id}",
    "messages": [
      {
        "prompt": "First message in batch",
        "system_prompt": "You are a helpful assistant"
      },
      {
        "prompt": "Second message in batch", 
        "system_prompt": "You are a helpful assistant"
      },
      {
        "prompt": "Third message in batch",
        "system_prompt": "You are a helpful assistant"
      }
    ]
  }'
```

### 5. Create Batch Aggregator Worker
```bash
curl -X POST http://localhost:8501/api/v1/worker/create/batch_aggregator \
  -H "Content-Type: application/json" \
  -d '{
    "count": 1
  }'
```

### 6. Check Message Status
```bash
# Replace {message_id} with message_id from step 3 or 4 response
curl http://localhost:8501/api/v1/message/read/{message_id}
```

### 7. Get Batch Results
```bash
# Replace {batch_id} with batch_id from step 4 response
curl http://localhost:8501/api/v1/batch/{batch_id}/results
```

### 8. Get Batch Results as CSV
```bash
# Replace {batch_id} with batch_id from step 4 response
curl "http://localhost:8501/api/v1/batch/{batch_id}/results?format=csv"
```

## 📝 Queue Management

### Get All Queues
```bash
curl http://localhost:8501/api/v1/queues/
```

### Get Queue by ID
```bash
curl http://localhost:8501/api/v1/queue/{queue_id}
```

### Delete Queue
```bash
curl -X DELETE http://localhost:8501/api/v1/queue/delete/{queue_id}
```

## 🔥 APISIX AI Gateway Testing

### Test AI Route (Single Request)
```bash
# Replace {queue_id} and {model_name} with actual values from queue creation response
curl -X POST http://localhost:9080/{queue_id}-{model_name} \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is a test message"
      }
    ]
  }'
```

### Test Rate Limiting (Multiple Requests)
```bash
# Send 15 requests quickly to test rate limiting (should see 429 errors after limit)
for i in {1..15}; do
  echo "Request $i:"
  curl -X POST http://localhost:9080/{queue_id}-{model_name} \
    -H "Content-Type: application/json" \
    -d "{
      \"messages\": [
        {
          \"role\": \"user\",
          \"content\": \"Test message $i\"
        }
      ]
    }"
  echo -e "\n---"
  sleep 1
done
```

### Test Rate Limiting (Parallel Requests)
```bash
# Send multiple requests in parallel to test burst limits
for i in {1..20}; do
  curl -X POST http://localhost:9080/{queue_id}-{model_name} \
    -H "Content-Type: application/json" \
    -d "{
      \"messages\": [
        {
          \"role\": \"user\",
          \"content\": \"Parallel test $i\"
        }
      ]
    }" &
done
wait
```

## 🔧 APISIX Admin API

### Check All Routes
```bash
curl -X GET http://localhost:9180/apisix/admin/routes \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```

### Check Specific Route
```bash
curl -X GET http://localhost:9180/apisix/admin/routes/route-{queue_id} \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```

### Check Route Configuration
```bash
curl -X GET http://localhost:9180/apisix/admin/routes/route-{queue_id} \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" | jq '.plugins'
```

## 📊 Example Test Flow

### 1. Create a test queue
```bash
curl -X POST http://localhost:8501/api/v1/queue/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "my-test-queue",
    "providers": [
      {
        "provider_name": "OpenAI Test",
        "provider_type": "openai",
        "api_key": "sk-test123456789",
        "limit": 5,
        "time_window": 60,
        "config": {
          "model": "gpt-3.5-turbo"
        }
      }
    ]
  }'
```

### 2. Note the queue_id from response, then test the route
```bash
# Use the queue_id from step 1 response
curl -X POST http://localhost:9080/YOUR_QUEUE_ID-gpt-3-5-turbo \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello, test message"
      }
    ]
  }'
```

### 3. Test rate limiting (should get 429 after 5 requests)
```bash
for i in {1..8}; do
  echo "Request $i:"
  curl -X POST http://localhost:9080/YOUR_QUEUE_ID-gpt-3-5-turbo \
    -H "Content-Type: application/json" \
    -d "{
      \"messages\": [
        {
          \"role\": \"user\",
          \"content\": \"Rate limit test $i\"
        }
      ]
    }"
  echo -e "\n---"
done
```

## 🐛 Troubleshooting

### Check Service Status
```bash
docker ps
docker logs ai_rate_limiter_app
docker logs ai_rate_limiter_apisix
```

### Verify APISIX is Working
```bash
curl http://localhost:9180/apisix/admin/plugins \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```

### Check if Route Exists
```bash
# Replace {queue_id} with actual queue ID
curl -X GET http://localhost:9180/apisix/admin/routes/route-{queue_id} \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1"
```