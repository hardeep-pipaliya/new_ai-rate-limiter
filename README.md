# AI Rate Limiter

A comprehensive Flask-based AI rate limiting and batch processing system with Redis caching, RabbitMQ queuing, PostgreSQL persistence, and APISIX AI rate limiting.

## 🚀 Features

- **AI Rate Limiting**: Advanced rate limiting with APISIX AI rate limiting plugin
- **Queue-Based Routing**: Dynamic routing with `/queue/{queue_id}` structure
- **Queue-Model Routing**: Specific routing with `/queue/{queue_id}/{model_name}` structure
- **Dynamic Rate Limiting**: Configurable token limits and time windows per route
- **Queue Name Support**: Create queues with descriptive names instead of UUIDs
- **Multiple LLM Providers**: Support for OpenAI, Azure, Anthropic, DeepSeek, and Claude
- **Mock API Testing**: Built-in mock OpenAI API for testing
- **Dynamic Queue Management**: Create and manage message queues with multiple AI providers
- **Batch Processing**: Process large batches of messages with progress tracking
- **Webhook Support**: Real-time notifications for batch completion
- **Worker Management**: Dynamic Celery worker creation and monitoring
- **Export Options**: CSV and JSON export for batch results
- **Docker Support**: Complete containerized deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask App     │    │   RabbitMQ      │    │   Celery        │
│   (API Layer)   │───▶│   (Message      │───▶│   Workers       │
│                 │    │   Queue)        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Redis         │    │   APISIX        │
│   (Database)    │    │   (Cache &      │    │   (AI Rate      │
│                 │    │   Counters)     │    │   Limiting)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git
- API Keys for LLM providers (OpenAI, Azure, Anthropic, DeepSeek, Claude)

## 🛠️ Installation

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai_rate_limiter.git
   cd ai_rate_limiter
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Setup APISIX AI Rate Limiting**
   ```bash
   # Wait for APISIX to start, then run:
   docker exec ai_rate_limiter_app python setup_apisix_ai_limiting.py
   ```

5. **Initialize the database**
   ```bash
   docker-compose exec flask_app flask db upgrade
   ```

### Option 2: Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai_rate_limiter.git
   cd ai_rate_limiter
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Start required services** (PostgreSQL, Redis, RabbitMQ, APISIX)

6. **Setup APISIX AI Rate Limiting**
   ```bash
   python setup_apisix_ai_limiting.py
   ```

7. **Run the application**
   ```bash
   python run.py
   ```

8. **Run Celery worker** (in another terminal)
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

## 🔧 Configuration

### Environment Variables

Add your API keys to the `.env` file:

```bash
# LLM Provider API Keys (Mock for testing)
OPENAI_API_KEY=sk-vj0klhb2p75gbrrhouij7jq3y8uqvok
OPENAI_API_BASE=https://mockgpt.wiremockapi.cloud/v1
AZURE_API_KEY=your_azure_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

### APISIX Routes

The system creates three types of routes:

1. **Provider-specific routes**: `/v1/chat/completions/{provider}`
   - Direct access to specific LLM providers
   - Individual rate limiting per provider

2. **Queue-based routes**: `/v1/chat/completions/queue/{queue_id}`
   - Multi-provider routing with load balancing
   - Queue-specific rate limiting

3. **Queue-Model routes**: `/v1/chat/completions/queue/{queue_id}/{model_name}`
   - Specific model routing within a queue
   - Custom rate limiting per queue-model combination

### Dynamic Rate Limiting

Each route supports configurable rate limiting parameters:

```json
{
  "limit_strategy": "total_tokens",
  "limit": 100,        // Token limit
  "time_window": 30    // Time window in seconds
}
```

## 📡 API Usage

### Create Queue with queue_id (Original Method)

```bash
curl -X POST http://localhost:8501/api/v1/queue/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "550e8400-e29b-41d4-a716-446655440000",
    "providers": [
      {
        "provider_name": "OpenAI Mock",
        "provider_type": "openai",
        "api_key": "sk-vj0klhb2p75gbrrhouij7jq3y8uqvok",
        "limit": 100,
        "time_window": 30,
        "config": {
          "model": "gpt-3.5-turbo",
          "endpoint": "https://mockgpt.wiremockapi.cloud/v1"
        }
      }
    ]
  }'
```

### Create Queue with queue_name (New Method)

```bash
curl -X POST http://localhost:8501/api/v1/queue/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "production-queue",
    "providers": [
      {
        "provider_name": "OpenAI Mock",
        "provider_type": "openai",
        "api_key": "sk-vj0klhb2p75gbrrhouij7jq3y8uqvok",
        "limit": 100,
        "time_window": 30,
        "config": {
          "model": "gpt-3.5-turbo",
          "endpoint": "https://mockgpt.wiremockapi.cloud/v1"
        }
      }
    ]
  }'
```

### Create a Single Message

```bash
curl -X POST http://localhost:8501/api/v1/message/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "Hello, how are you?",
    "system_prompt": "You are a helpful assistant",
    "supportive_variable": {
      "priority": "high",
      "test": "single_message"
    }
  }'
```

### Create Batch Messages

```bash
curl -X POST http://localhost:8501/api/v1/message/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_id": "550e8400-e29b-41d4-a716-446655440000",
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
    ],
    "supportive_variable": {
      "order": 1,
      "test": "batch_messages"
    }
  }'
```

### Get Message Status

```bash
curl http://localhost:8501/api/v1/message/read/{message_id}
```

### Get Batch Results

```bash
curl http://localhost:8501/api/v1/batch/{batch_id}/messages
```

## 🔍 Monitoring

### Health Check

```bash
curl http://localhost:8501/health
```

### APISIX Admin API

```bash
# List all routes
curl http://localhost:9180/apisix/admin/routes

# Get specific route
curl http://localhost:9180/apisix/admin/routes/{route_id}
```

### Direct APISIX Testing

```bash
# Test OpenAI route
curl -X POST http://localhost:9080/v1/chat/completions/openai \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-vj0klhb2p75gbrrhouij7jq3y8uqvok" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'

# Test queue-model route
curl -X POST http://localhost:9080/v1/chat/completions/queue/test-queue-123/openai \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-vj0klhb2p75gbrrhouij7jq3y8uqvok" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'
```

## 🚀 Deployment

### Production Deployment

1. **Update environment variables**
   ```bash
   # Set production values in .env
   FLASK_ENV=production
   SECRET_KEY=your_secure_secret_key
   ```

2. **Start with production settings**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

3. **Setup APISIX**
   ```bash
   docker exec ai_rate_limiter_app python setup_apisix_ai_limiting.py
   ```

## 📊 Rate Limiting

The system implements multiple layers of rate limiting:

1. **APISIX AI Rate Limiting**: Per-provider token limits with configurable time windows
2. **Request Rate Limiting**: Requests per second
3. **Connection Limiting**: Concurrent connections
4. **Queue-based Limiting**: Per-queue rate limits
5. **Dynamic Rate Limiting**: Custom limits per queue-model combination

### Dynamic Rate Limiting Configuration

```bash
# Create route with custom rate limiting
curl -X PUT http://localhost:9180/apisix/admin/routes/queue-test-123-openai \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "queue-test-123-openai",
    "uri": "/v1/chat/completions/queue/test-123/openai",
    "plugins": {
      "ai-rate-limiting": {
        "instances": [
          {
            "name": "openai-instance",
            "provider": "openai",
            "limit_strategy": "total_tokens",
            "limit": 150,
            "time_window": 45,
            "auth": {
              "header": {
                "Authorization": "Bearer sk-vj0klhb2p75gbrrhouij7jq3y8uqvok"
              }
            },
            "options": {
              "model": "gpt-3.5-turbo",
              "base_url": "https://mockgpt.wiremockapi.cloud/v1"
            }
          }
        ]
      }
    }
  }'
```

## 🧪 Testing

### Run Comprehensive Tests

```bash
python test_ai_limiting.py
```

### Test Specific Features

```bash
# Test queue creation with queue_name
curl -X POST http://localhost:8501/queue/create \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "test-queue-with-name",
    "providers": [
      {
        "provider_name": "OpenAI Mock",
        "provider_type": "openai",
        "api_key": "sk-vj0klhb2p75gbrrhouij7jq3y8uqvok",
        "limit": 100,
        "time_window": 30,
        "config": {
          "model": "gpt-3.5-turbo",
          "endpoint": "https://mockgpt.wiremockapi.cloud/v1"
        }
      }
    ]
  }'

# Test queue-model routing
curl -X POST http://localhost:8501/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing",
    "queue_id": "550e8400-e29b-41d4-a716-446655440000",
    "model_name": "openai",
    "system_prompt": "You are an expert in quantum computing",
    "supportive_variable": {
      "priority": "high",
      "topic": "quantum_computing"
    }
  }'
```

## 🔧 Troubleshooting

### Common Issues

1. **APISIX not starting**
   ```bash
   docker logs ai_rate_limiter_apisix
   ```

2. **Database connection issues**
   ```bash
   docker-compose down -v
   docker-compose up --build
   ```

3. **API key issues**
   - Verify all API keys are set in `.env`
   - Check provider-specific error messages

4. **Rate limiting issues**
   - Check APISIX route configuration
   - Verify token limits and time windows
   - Test direct APISIX calls

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs flask_app
docker-compose logs celery_worker
docker-compose logs apisix
```

### Test Direct API Call (Bypass APISIX)

```bash
# Test direct OpenAI API
curl -X POST https://mockgpt.wiremockapi.cloud/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-vj0klhb2p75gbrrhouij7jq3y8uqvok" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


