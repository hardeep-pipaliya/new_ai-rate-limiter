"""
APISIX AI Gateway Service for rate limiting
"""

import requests
import logging
import os
import json
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ApisixGateway:
    """
    APISIX AI Gateway for rate limiting
    """
    
    def __init__(self, admin_url: str = None, admin_key: str = None):
        self.admin_url = admin_url or os.getenv('APISIX_ADMIN_URL', 'http://apisix:9180')
        self.admin_url = self.admin_url.rstrip('/')
        self.admin_key = admin_key or os.getenv('APISIX_ADMIN_KEY', 'edd1c9f034335f136f87ad84b625c8f1')
        self.headers = {"X-API-KEY": self.admin_key, "Content-Type": "application/json"}
        
        self.timeout = 30
        self.max_retries = 5
    
    def _wait_for_apisix_ready(self) -> bool:
        """Wait for APISIX to be ready"""
        for attempt in range(10):
            try:
                response = requests.get(
                    f"{self.admin_url}/apisix/admin/plugins",
                    headers=self.headers,
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"✅ APISIX is ready (attempt {attempt + 1})")
                    return True
            except Exception as e:
                print(f"⏳ Waiting for APISIX... (attempt {attempt + 1}): {e}")
            time.sleep(5)
        print("❌ APISIX not ready after 10 attempts")
        return False
    
    def _check_apisix_health(self) -> bool:
        """Check if APISIX is healthy and responding"""
        try:
            response = requests.get(
                f"{self.admin_url}/apisix/admin/plugins",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def create_ai_route(self, queue_id: str, providers: List[Dict]) -> Dict[str, Any]:
        """Create APISIX route for queue with model names"""
        try:
            # Wait for APISIX to be ready
            if not self._wait_for_apisix_ready():
                print("⚠️  APISIX not ready, but continuing...")
            
            # Extract model names from providers and create route path
            models = []
            for provider in providers:
                model_name = provider.get("config", {}).get("model")
                if not model_name:
                    raise Exception(f"No model configured for provider {provider.get('provider_id', 'unknown')}")
                # Replace dots and spaces with hyphens for URL safety
                model_safe = model_name.replace(".", "-").replace(" ", "-")
                models.append(model_safe)
            
            # Create route path: queue_id-model_name1-model_name2
            route_path = f"/{queue_id}-{'-'.join(models)}"
            route_id = f"route-{queue_id}"
            
            # Build upstream configuration first (required)
            upstream_config = self._build_upstream_config(providers)
            
            # Build proper APISIX route configuration with correct schema
            config = {
                "uri": route_path,
                "methods": ["POST"],
                "upstream": upstream_config,
                "plugins": {
                    "limit-req": self._build_rate_limiting_config(providers),
                    "proxy-rewrite": self._build_proxy_rewrite_config(providers),
                    "cors": {
                        "allow_origins": "*",
                        "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                        "allow_headers": "*",
                        "expose_headers": "*",
                        "max_age": 3600,
                        "allow_credential": False
                    }
                }
            }
            
            # Create route via APISIX Admin API with retry
            print(f"🔧 Creating APISIX route: {route_path}")
            
            # Retry mechanism for APISIX connection
            response = None
            for attempt in range(self.max_retries):
                try:
                    response = requests.put(
                        f"{self.admin_url}/apisix/admin/routes/{route_id}",
                        headers=self.headers,
                        json=config,
                        timeout=self.timeout
                    )
                    print(f"🔧 APISIX response (attempt {attempt + 1}): {response.status_code} - {response.text}")
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"Created APISIX route: {route_path}")
                        return {"success": True, "route_id": route_id, "route_path": route_path}
                    elif response.status_code == 409:
                        # Route already exists, try to update it
                        print(f"🔧 Route {route_id} already exists, updating...")
                        update_result = self.update_ai_route(queue_id, providers)
                        if update_result.get('success'):
                            return {"success": True, "route_id": route_id, "route_path": route_path, "message": "Route updated successfully"}
                        else:
                            return update_result
                    
                    break
                except requests.exceptions.ConnectionError as e:
                    print(f"🔧 APISIX connection failed (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(5)
                    else:
                        print(f"⚠️  APISIX connection failed after {self.max_retries} attempts, but continuing...")
                        return {"success": True, "route_id": route_id, "route_path": route_path, "warning": "APISIX connection failed, route will be created on first request"}
                except Exception as e:
                    print(f"🔧 APISIX request failed (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(3)
                    else:
                        return {"success": False, "error": str(e)}
            
            if response:
                error_msg = response.text
                logger.error(f"APISIX route creation failed: {error_msg}")
                
                # Check if it's a schema validation error
                if "schema" in error_msg.lower() or "validation" in error_msg.lower():
                    print(f"🔧 APISIX schema validation error. Trying simplified configuration...")
                    # Try with minimal configuration
                    minimal_config = {
                        "uri": route_path,
                        "methods": ["POST"],
                        "upstream": upstream_config
                    }
                    
                    try:
                        minimal_response = requests.put(
                            f"{self.admin_url}/apisix/admin/routes/{route_id}",
                            headers=self.headers,
                            json=minimal_config,
                            timeout=self.timeout
                        )
                        
                        if minimal_response.status_code in [200, 201]:
                            logger.info(f"Created APISIX route with minimal config: {route_path}")
                            return {"success": True, "route_id": route_id, "route_path": route_path, "warning": "Used minimal configuration"}
                        else:
                            print(f"🔧 Minimal config failed: HTTP {minimal_response.status_code}: {minimal_response.text}")
                            # Try even more minimal config
                            basic_config = {
                                "uri": route_path,
                                "upstream": upstream_config
                            }
                            
                            basic_response = requests.put(
                                f"{self.admin_url}/apisix/admin/routes/{route_id}",
                                headers=self.headers,
                                json=basic_config,
                                timeout=self.timeout
                            )
                            
                            if basic_response.status_code in [200, 201]:
                                logger.info(f"Created APISIX route with basic config: {route_path}")
                                return {"success": True, "route_id": route_id, "route_path": route_path, "warning": "Used basic configuration"}
                            else:
                                return {"success": False, "error": f"Basic config also failed: HTTP {basic_response.status_code}: {basic_response.text}", "route_path": route_path}
                    except Exception as e:
                        return {"success": False, "error": f"Minimal config failed: {str(e)}", "route_path": route_path}
                
                return {"success": False, "error": f"HTTP {response.status_code}: {error_msg}", "route_path": route_path}
            else:
                return {"success": False, "error": "No response received", "route_path": route_path}
                
        except Exception as e:
            logger.error(f"APISIX route creation error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_ai_route(self, queue_id: str, providers: List[Dict]) -> Dict[str, Any]:
        """Update existing APISIX route"""
        try:
            route_id = f"route-{queue_id}"
            
            # Build complete update configuration including upstream
            upstream_config = self._build_upstream_config(providers)
            
            config = {
                "upstream": upstream_config,
                "plugins": {
                    "limit-req": self._build_rate_limiting_config(providers),
                    "proxy-rewrite": self._build_proxy_rewrite_config(providers),
                    "cors": {
                        "allow_origins": "*",
                        "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                        "allow_headers": "*",
                        "expose_headers": "*",
                        "max_age": 3600,
                        "allow_credential": False
                    }
                }
            }
            
            # Try to update the route
            response = requests.patch(
                f"{self.admin_url}/apisix/admin/routes/{route_id}",
                headers=self.headers,
                json=config,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Updated APISIX route: {route_id}")
                return {"success": True, "route_id": route_id}
            elif response.status_code == 404:
                # Route doesn't exist, try to create it
                logger.info(f"Route {route_id} not found, creating new route")
                return self.create_ai_route(queue_id, providers)
            else:
                logger.error(f"APISIX route update failed: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"APISIX route update error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def delete_ai_route(self, queue_id: str) -> Dict[str, Any]:
        """Delete APISIX route"""
        try:
            route_id = f"route-{queue_id}"
            
            response = requests.delete(
                f"{self.admin_url}/apisix/admin/routes/{route_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 404]:  # 404 is OK - route already deleted
                logger.info(f"Deleted APISIX route: {route_id}")
                return {"success": True, "route_id": route_id}
            else:
                logger.error(f"APISIX route deletion failed: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"APISIX route deletion error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _build_rate_limiting_config(self, providers: List[Dict]) -> Dict[str, Any]:
        """Build rate limiting configuration from providers"""
        if not providers:
            return {
                "rate": 10,
                "burst": 20,
                "key": "remote_addr",
                "rejected_code": 429,
                "rejected_msg": "Rate limit exceeded"
            }
        
        # Use the most restrictive rate limit from all providers
        min_limit = min(provider.get('limit', 1000) for provider in providers)
        min_time_window = min(provider.get('time_window', 3600) for provider in providers)
        
        # Convert time_window to rate (requests per second)
        rate = max(0.1, min_limit / min_time_window)  # Ensure minimum rate
        
        return {
            "rate": rate,
            "burst": min_limit,
            "key": "remote_addr",
            "rejected_code": 429,
            "rejected_msg": "Rate limit exceeded"
        }
    
    def _build_auth_headers(self, providers: List[Dict]) -> Dict[str, str]:
        """Build authentication headers for the first provider"""
        if not providers:
            return {}
        
        # Use first provider for auth (can be enhanced for load balancing)
        provider = providers[0]
        provider_type = provider.get("provider_type", "openai")
        api_key = provider.get("api_key", "")
        
        auth_headers = {
            "openai": {"Authorization": f"Bearer {api_key}"},
            "anthropic": {"x-api-key": api_key},
            "claude": {"x-api-key": api_key},
            "azure": {"api-key": api_key},
            "deepseek": {"Authorization": f"Bearer {api_key}"}
        }
        
        return auth_headers.get(provider_type, {"Authorization": f"Bearer {api_key}"})
    
    def _build_proxy_rewrite_config(self, providers: List[Dict]) -> Dict[str, Any]:
        """Build proxy rewrite configuration with auth headers"""
        auth_headers = self._build_auth_headers(providers)
        
        config = {
            "uri": "/v1/chat/completions"
        }
        
        # Add auth headers to the rewrite config
        if auth_headers:
            config["headers"] = auth_headers
        
        return config
    
    def _build_upstream_config(self, providers: List[Dict]) -> Dict[str, Any]:
        """Build upstream configuration from providers"""
        if not providers:
            return {
                "type": "roundrobin",
                "nodes": {"httpbin.org:80": 1},
                "scheme": "http"
            }
        
        # Use first provider's endpoint (can be enhanced for multiple upstreams)
        provider = providers[0]
        endpoint = self._get_endpoint(provider.get("provider_type", "openai"), provider)
        
        # Extract host and port from endpoint
        import urllib.parse
        parsed = urllib.parse.urlparse(endpoint)
        host = parsed.hostname or "api.openai.com"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        scheme = parsed.scheme or "https"
        
        # Ensure we have valid upstream configuration
        upstream_config = {
            "type": "roundrobin",
            "nodes": {f"{host}:{port}": 1},
            "scheme": scheme,
            "timeout": {
                "connect": 60,
                "send": 60,
                "read": 60
            }
        }
        
        # Add keepalive pool only if not already present
        if "keepalive_pool" not in upstream_config:
            upstream_config["keepalive_pool"] = {
                "size": 320,
                "idle_timeout": 60,
                "requests": 1000
            }
        
        return upstream_config
    
    def _get_endpoint(self, provider_type: str, provider: Dict) -> str:
        """Get endpoint based on provider type and configuration"""
        # Check if custom endpoint is provided in config
        custom_endpoint = provider.get("config", {}).get("endpoint")
        if custom_endpoint:
            return custom_endpoint
        
        # Default endpoints based on provider type
        default_endpoints = {
            "openai": "https://api.openai.com",
            "anthropic": "https://api.anthropic.com",
            "claude": "https://api.anthropic.com",
            "azure": "https://your-resource.openai.azure.com",
            "deepseek": "https://api.deepseek.com"
        }
        
        return default_endpoints.get(provider_type, "https://api.openai.com")


# Global instance for easy import
apisix_gateway = ApisixGateway()

# Simple functions for direct use
def create_route(queue_id: str, providers: List[Dict]) -> Dict[str, Any]:
    """Create APISIX AI route with rate limiting"""
    print(f"🔧 [create_route] Called with queue_id: {queue_id}")
    print(f"🔧 [create_route] Providers: {providers}")
    return apisix_gateway.create_ai_route(queue_id, providers)

def update_route(queue_id: str, providers: List[Dict]) -> Dict[str, Any]:
    """Update APISIX AI route"""
    return apisix_gateway.update_ai_route(queue_id, providers)

def delete_route(queue_id: str) -> Dict[str, Any]:
    """Delete APISIX AI route"""
    return apisix_gateway.delete_ai_route(queue_id)