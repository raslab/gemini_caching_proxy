from fastapi import FastAPI, Request, Response, HTTPException
import httpx
import pymongo
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = FastAPI()

# MongoDB connection setup
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "gemini_proxy_db"
COLLECTION_NAME = "gemini_interactions"

# Gemini API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables or .env file.")
    print("Please set the GEMINI_API_KEY environment variable or add it to a .env file.")


try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    print("MongoDB connected successfully!")
except pymongo.errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    # Depending on requirements, you might want to exit or handle this differently
    # For now, we'll allow the app to start but logging will fail.

# Target Gemini API base URL
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com" # This might need adjustment based on specific endpoints

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy_gemini_api(full_path: str, request: Request):
    """
    Proxies requests to the Gemini API, logs them, and returns the response.
    """
    start_time = datetime.now()

    # Log incoming request
    request_data = {
        "timestamp": start_time,
        "method": request.method,
        "path": "/" + full_path,
        "headers": dict(request.headers),
        "body": await request.json() if request.headers.get('content-type') == 'application/json' else (await request.body()).decode()
    }

    # Forward request to Gemini API
    gemini_url = f"{GEMINI_API_BASE_URL}/{full_path}"
    try:
        async with httpx.AsyncClient() as client:
            # Recreate headers, removing host and potentially others that shouldn't be forwarded
            forward_headers = {name: value for name, value in request.headers.items() if name.lower() not in ["host", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"]}

            # Add Gemini API key to headers (or query parameters, depending on API)
            # The Gemini API typically uses the API key in the query parameters or a header like 'x-goog-api-key'
            # We'll add it to query parameters for simplicity, adjust if needed based on exact endpoint requirements
            params = dict(request.query_params)
            if GEMINI_API_KEY:
                params["key"] = GEMINI_API_KEY

            # Handle streaming requests
            if 'text/event-stream' in request.headers.get('accept', ''):
                print(f"Handling streaming request to {gemini_url}")
                # Forward the request and stream the response back
                async with client.stream(
                    method=request.method,
                    url=gemini_url,
                    headers=forward_headers,
                    params=params, # Include params here
                    content=await request.body()
                ) as gemini_response:
                    # Ensure the response is successful before streaming
                    gemini_response.raise_for_status()

                    # Prepare the response to the client
                    response_headers = dict(gemini_response.headers)
                    # Remove headers that might cause issues with streaming to the client
                    response_headers.pop('content-length', None)
                    response_headers.pop('transfer-encoding', None)
                    response_headers.pop('content-encoding', None) # ADDED: Prevent client decompression issues

                    async def stream_response():
                        full_response_body = b""
                        async for chunk in gemini_response.aiter_bytes():
                            full_response_body += chunk
                            yield chunk

                        # Log the full accumulated response after streaming is complete
                        end_time = datetime.now()
                        duration_ms = (end_time - start_time).total_seconds() * 1000

                        response_data = {
                            "status": gemini_response.status_code,
                            "headers": dict(gemini_response.headers),
                            "body": full_response_body.decode('utf-8', errors='ignore') # Decode for logging
                        }

                        # Extract generation settings and usage metadata (basic example, needs refinement)
                        # Note: For streaming, usage metadata might be in the last chunk or headers
                        # generation_settings = request_data.get("body", {}).get("generationConfig")
                        # Attempt to find usage metadata in headers or accumulated body (requires parsing)
                        # usage_metadata = response_data.get("body", {}).get("usageMetadata") # This might not work directly for streamed bodies

                        log_entry = {
                            "timestamp": start_time,
                            "request": request_data,
                            "response": response_data,
                            "request_duration_ms": duration_ms,
                            # "generation_settings": generation_settings,
                            # "usage_metadata": usage_metadata,
                            "error": None
                        }

                        try:
                            collection.insert_one(log_entry)
                            print("Logged streaming interaction to MongoDB")
                        except Exception as db_error:
                            print(f"Error saving streaming interaction to MongoDB: {db_error}")

                    # Return the streaming response
                    return Response(
                        content=stream_response(),
                        status_code=gemini_response.status_code,
                        headers=response_headers,
                    )
            else:
                # Handle non-streaming requests
                print(f"Handling non-streaming request to {gemini_url}")
                gemini_response = await client.request(
                    method=request.method,
                    url=gemini_url,
                    headers=forward_headers,
                    params=params, # Include params here
                    content=await request.body(),
                    timeout=300
                )
                gemini_response.raise_for_status() # Raise an exception for bad status codes

                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                # Log response
                response_data = {
                    "status": gemini_response.status_code,
                    "headers": dict(gemini_response.headers),
                    "body": gemini_response.json() if 'application/json' in gemini_response.headers.get('content-type', '') else gemini_response.text
                }

                # Extract generation settings and usage metadata
                generation_settings = None
                if isinstance(request_data.get("body"), dict):
                    generation_settings = request_data["body"].get("generationConfig")

                usage_metadata = None
                if isinstance(response_data.get("body"), dict):
                     usage_metadata = response_data["body"].get("usageMetadata")

                log_entry = {
                    "timestamp": start_time,
                    "request": request_data,
                    "response": response_data,
                    "request_duration_ms": duration_ms,
                    "generation_settings": generation_settings,
                    "usage_metadata": usage_metadata,
                    "error": None
                }

                # Save to MongoDB
                try:
                    collection.insert_one(log_entry)
                    print("Logged non-streaming interaction to MongoDB")
                except Exception as db_error:
                    print(f"Error saving non-streaming interaction to MongoDB: {db_error}")

                # Return response to client
                response_headers = dict(gemini_response.headers)
                response_headers.pop('content-encoding', None) # ADDED: Prevent client decompression issues
                return Response(
                    content=gemini_response.content,
                    status_code=gemini_response.status_code,
                    headers=response_headers,
                )

    except Exception as e:
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        error_message = f"HTTP request failed: {e.__class__.__name__} - {str(e)}"
        print(error_message)

        log_entry = {
            "timestamp": start_time,
            "request": request_data,
            "response": None, # No response received
            "request_duration_ms": duration_ms,
            "generation_settings": request_data.get("body", {}).get("generationConfig"),
            "usage_metadata": None,
            "error": {
                "message": error_message,
                "details": str(e)
            }
        }

        # Save error to MongoDB
        try:
            collection.insert_one(log_entry)
            print("Logged error interaction to MongoDB")
        except Exception as db_error:
            print(f"Error saving error to MongoDB: {db_error}")

        raise HTTPException(status_code=500, detail=f"Proxy error: {e}")
    except Exception as e:
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        error_message = f"An unexpected error occurred: {e}"
        print(error_message)

        log_entry = {
            "timestamp": start_time,
            "request": request_data,
            "response": None, # No response received
            "request_duration_ms": duration_ms,
            "generation_settings": request_data.get("body", {}).get("generationConfig"),
            "usage_metadata": None,
            "error": {
                "message": error_message,
                "details": str(e)
            }
        }

        # Save error to MongoDB
        try:
            collection.insert_one(log_entry)
            print("Logged unexpected error interaction to MongoDB")
        except Exception as db_error:
            print(f"Error saving unexpected error to MongoDB: {db_error}")

        raise HTTPException(status_code=500, detail=f"An unexpected proxy error occurred: {e}")

# Basic root endpoint
@app.get("/")
async def read_root():
    return {"message": "Gemini API Proxy is running"}
