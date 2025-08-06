# Rate Limiting Test Commands

## 1. Create a Queue with Rate Limiting

```bash
curl -X POST "http://localhost:8501/api/v1/queue/create" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "test-rate-limit-queue",
    "providers": [
      {
        "provider_name": "OpenAI Test Provider",
        "provider_type": "openai",
        "api_key": "sk-test-key",
        "limit": 5,
        "time_window": 60,
        "config": {
          "model": "gpt-3.5-turbo"
        }
      }
    ]
  }'
```

## 2. Test Rate Limiting (Replace QUEUE_ID with actual queue ID from step 1)

```bash
# Test 1: First request (should succeed)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 1"
      }
    ]
  }'

# Test 2: Second request (should succeed)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 2"
      }
    ]
  }'

# Test 3: Third request (should succeed)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 3"
      }
    ]
  }'

# Test 4: Fourth request (should succeed)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 4"
      }
    ]
  }'

# Test 5: Fifth request (should succeed)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 5"
      }
    ]
  }'

# Test 6: Sixth request (should be rate limited - 429)
curl -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, this is test message 6"
      }
    ]
  }'
```

## 3. Test Message Creation Through API

```bash
# Create a message (Replace QUEUE_ID with actual queue ID)
curl -X POST "http://localhost:8501/api/v1/message/create" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "QUEUE_ID",
    "prompt": "Hello, this is a test message for rate limiting",
    "system_prompt": "You are a helpful assistant"
  }'
```

## 4. Check Message Status (Replace MESSAGE_ID with actual message ID)

```bash
curl -X GET "http://localhost:8501/api/v1/message/MESSAGE_ID"
```

## Expected Results:

1. **Queue Creation**: Should return success with queue_id and route_path
2. **Rate Limiting**: 
   - First 5 requests: HTTP 200 (success)
   - 6th request onwards: HTTP 429 (rate limited)
3. **Message Creation**: Should return success with message_id and provider_id set
4. **Message Status**: Should show completed status with result

## Quick Test Script:

```bash
# Run this to test rate limiting quickly
for i in {1..10}; do
  echo "Request $i/10"
  curl -s -w "HTTP Status: %{http_code}\n" -X POST "http://localhost:9080/QUEUE_ID-gpt-3-5-turbo" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-3.5-turbo",
      "messages": [{"role": "user", "content": "Test message '$i'"}]
    }'
  sleep 1
done
```

## Troubleshooting:

1. **If routes return 404**: Check if APISIX is running and routes are created
2. **If no rate limiting**: Check APISIX logs for configuration errors
3. **If provider_id is null**: Check if provider is properly associated with queue
4. **Permission denied errors**: APISIX is now configured to run as root and disable debug logs
