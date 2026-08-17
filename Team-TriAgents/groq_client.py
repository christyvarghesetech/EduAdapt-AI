import os
import time
import re
from groq import Groq as OriginalGroq
from dotenv import load_dotenv

load_dotenv()

def is_valid_key_format(key: str) -> bool:
    k = key.strip().strip("'").strip('"')
    if not k.startswith("gsk_"):
        return False
    if "your" in k.lower() or "placeholder" in k.lower() or "mock" in k.lower() or "second" in k.lower() or "third" in k.lower():
        return False
    return len(k) > 10

# Global list of keys
raw_keys = os.environ.get("GROQ_API_KEY", "")
api_keys = []

if raw_keys:
    # Support comma-separated pool
    for k in raw_keys.split(","):
        k_clean = k.strip().strip("'").strip('"')
        if is_valid_key_format(k_clean):
            api_keys.append(k_clean)

# Also check for individual numbered keys (e.g. GROQ_API_KEY_1, GROQ_API_KEY_2)
for i in range(1, 15):
    numbered_key = os.environ.get(f"GROQ_API_KEY_{i}")
    if numbered_key:
        k_clean = numbered_key.strip().strip("'").strip('"')
        if is_valid_key_format(k_clean):
            api_keys.append(k_clean)

# Deduplicate keys
api_keys = list(dict.fromkeys(api_keys))

# If still empty, fall back to default or mock key
if not api_keys:
    fallback_key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY_1") or "MOCK_KEY"
    cleaned_fallback = fallback_key.strip().strip("'").strip('"')
    api_keys = [cleaned_fallback]

print(f"[Groq Client Manager] Initialized API key pool with {len(api_keys)} valid keys. Active key prefix: {api_keys[0][:10]}...")

# Key pointer index
current_key_idx = 0

class CompletionsWrapper:
    def create(self, *args, **kwargs):
        global current_key_idx
        max_retries = len(api_keys) * 2
        # Ensure we try at least 5 times to survive rate limits on a single key
        if len(api_keys) == 1:
            max_retries = 5
            
        last_exception = None
        
        # Check if caller originally requested JSON format
        wants_json = "response_format" in kwargs
        
        # Clone kwargs to allow mutating model/format parameters
        call_kwargs = dict(kwargs)
        
        for attempt in range(max_retries):
            key = api_keys[current_key_idx]
            try:
                # Pre-map decommissioned models to prevent unnecessary 404 network retries
                old_model = call_kwargs.get("model", "")
                if "70b" in old_model or "versatile" in old_model:
                    new_model = "groq/compound"
                elif "8b" in old_model or "instant" in old_model:
                    new_model = "groq/compound-mini"
                else:
                    new_model = old_model
                    
                if new_model != old_model:
                    print(f"[Groq Client Manager] Mapping decommissioned model '{old_model}' -> '{new_model}'")
                    call_kwargs["model"] = new_model
                    
                # Remove response_format if using groq/compound for compatibility
                if call_kwargs.get("model") == "groq/compound" and "response_format" in call_kwargs:
                    print("[Groq Client Manager] Removing response_format constraint for groq/compound compatibility.")
                    call_kwargs.pop("response_format", None)
                
                # Execute standard Groq client call
                client = OriginalGroq(api_key=key)
                response = client.chat.completions.create(*args, **call_kwargs)
                
                # If JSON format was requested, sanitize potential conversational wrappers or think blocks
                if wants_json and response.choices and response.choices[0].message.content:
                    raw_content = response.choices[0].message.content.strip()
                    
                    # Remove thinking tags <think>...</think> if present
                    raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
                    
                    # Remove markdown blocks ```json ... ```
                    if raw_content.startswith("```"):
                        lines = raw_content.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].startswith("```"):
                            lines = lines[:-1]
                        raw_content = "\n".join(lines).strip()
                        
                    # Extract the first matching JSON block object/array
                    match = re.search(r"(\{.*\}|\[.*\])", raw_content, re.DOTALL)
                    if match:
                        cleaned_json = match.group(0)
                        
                        # If it matched an array [ { ... } ], try to extract the inner object { ... } instead
                        if cleaned_json.startswith("[") and cleaned_json.endswith("]"):
                            inner_match = re.search(r"\{.*\}", cleaned_json, re.DOTALL)
                            if inner_match:
                                cleaned_json = inner_match.group(0)
                                
                        # Remove trailing commas that violate standard JSON
                        cleaned_json = re.sub(r",\s*([\]}])", r"\1", cleaned_json)
                        response.choices[0].message.content = cleaned_json
                        
                return response
                
            except Exception as e:
                last_exception = e
                err_msg = str(e)
                print(f"[Groq Key Rotator] Warning: API call failed on key index {current_key_idx} (Attempt {attempt + 1}/{max_retries}). Error: {err_msg}")
                
                # Check for rate limit error (429)
                is_rate_limit = "429" in err_msg or "rate limit" in err_msg.lower() or "rate_limit_exceeded" in err_msg
                is_model_error = "model_not_found" in err_msg or "does not exist" in err_msg or "decommissioned" in err_msg or "404" in err_msg or "400" in err_msg
                
                if is_model_error and call_kwargs.get("model") != "groq/compound" and call_kwargs.get("model") != "groq/compound-mini":
                    # Fallback mapping if not pre-mapped
                    old_model = call_kwargs.get("model", "")
                    if "70b" in old_model or "versatile" in old_model:
                        new_model = "groq/compound"
                    else:
                        new_model = "groq/compound-mini"
                    print(f"[Groq Client Manager] Fallback Mapping: '{old_model}' -> '{new_model}'")
                    call_kwargs["model"] = new_model
                    call_kwargs.pop("response_format", None)
                    
                    try:
                        client = OriginalGroq(api_key=key)
                        return client.chat.completions.create(*args, **call_kwargs)
                    except Exception as e2:
                        last_exception = e2
                        print(f"[Groq Key Rotator] Warning: Fallback model retry failed. Error: {e2}")
                
                # Dynamically parse the requested sleep duration from rate limit message
                wait_seconds = 2
                if is_rate_limit:
                    match_time = re.search(r"try again in (\d+\.?\d*)s", err_msg, re.IGNORECASE)
                    if match_time:
                        wait_seconds = float(match_time.group(1)) + 0.5
                        print(f"[Groq Key Rotator] Dynamic Rate Limit Recovery: Server requested {match_time.group(1)}s reset window. Sleeping {wait_seconds:.2f}s...")
                    else:
                        wait_seconds = 5
                        print(f"[Groq Key Rotator] Rate limit hit. Sleeping default {wait_seconds}s...")
                    
                    # Fallback to lighter model to bypass heavy rate limits on subsequent retries
                    if call_kwargs.get("model") == "groq/compound":
                        print("[Groq Key Rotator] Falling back to lighter model 'groq/compound-mini' to bypass rate limit.")
                        call_kwargs["model"] = "groq/compound-mini"
                
                # Rotate key if there are multiple keys
                if len(api_keys) > 1:
                    old_idx = current_key_idx
                    current_key_idx = (current_key_idx + 1) % len(api_keys)
                    print(f"[Groq Key Rotator] Rotating active key from index {old_idx} to index {current_key_idx} (sleeping {wait_seconds}s)...")
                    time.sleep(wait_seconds)
                else:
                    # Only one key, sleep and retry
                    print(f"[Groq Key Rotator] Only one key configured. Waiting {wait_seconds} seconds before retry...")
                    time.sleep(wait_seconds)
                    
        # If all retries failed, raise the final exception
        raise last_exception

class ChatWrapper:
    def __init__(self):
        self.completions = CompletionsWrapper()

class Groq:
    """
    Drop-in replacement wrapper for the standard Groq client class.
    Enforces automatic key rotation, model self-healing, and rate limit handling.
    """
    def __init__(self, api_key=None, **kwargs):
        self.chat = ChatWrapper()
