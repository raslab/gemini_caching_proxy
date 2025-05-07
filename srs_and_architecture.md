# Software Requirements Specification and Architecture Design for Gemini API Proxy

## 1. Introduction

This document outlines the requirements and architectural design for a local proxy application for the Gemini API. The proxy will run within a Docker container and intercept requests from clients (specifically the VS Code extension) to the Gemini API, log these requests and responses to a database, and then forward the response back to the client.

## 2. Functional Requirements

*   **FR-1: Request Interception:** The proxy SHALL intercept HTTP requests directed to the Gemini API.
*   **FR-2: Request Forwarding:** The proxy SHALL forward intercepted requests to the actual Gemini API endpoints.
*   **FR-3: Response Handling:** The proxy SHALL receive responses from the Gemini API.
*   **FR-4: Response Logging:** The proxy SHALL log the full request and response data, including headers, body, HTTP status code, and timing information, to a database.
*   **FR-5: Streaming Support:** The proxy SHALL handle streaming responses from the Gemini API and forward them to the client while simultaneously capturing the complete response for logging.
*   **FR-6: Response Forwarding:** The proxy SHALL forward the received response (including streaming data) back to the original client.
*   **FR-7: Data Storage:** The proxy SHALL store the logged data in a database capable of handling large records and a growing volume of data.
*   **FR-8: Error Handling:** The proxy SHALL handle errors gracefully, both from the Gemini API and the database, and log these errors.

## 3. Non-Functional Requirements

*   **NFR-1: Performance:** The proxy SHALL be able to handle up to 30 requests per minute, including streaming requests, without significant latency for the client.
*   **NFR-2: Scalability:** The chosen database SHALL be capable of storing up to 230 million tokens per month, with individual records potentially reaching 700,000 tokens or more.
*   **NFR-3: Ease of Use:** The application SHALL be easy to set up and run locally using Docker.
*   **NFR-4: Technology Stack:** The proxy SHALL be implemented using Python and the FastAPI framework.
*   **NFR-5: Data Persistence:** The logged data in the database SHALL persist across Docker container restarts.
*   **NFR-6: Extensibility:** The design SHOULD allow for the potential addition of other AI service providers in the future.
*   **NFR-7: Analytics Support:** The stored data SHOULD be structured in a way that facilitates future analysis of usage patterns.

## 4. Database Design (MongoDB)

Based on the requirement for ease of use, freeness, and handling large, flexible data structures, **MongoDB** is proposed as the database system.

**Proposed Collection: `gemini_interactions`**

Each document in this collection will represent a single request-response interaction with the Gemini API.

```json
{
  "_id": ObjectId, // MongoDB's unique document ID
  "timestamp": Date, // Timestamp when the request was received by the proxy
  "request": {
    "method": String, // HTTP method (e.g., "POST")
    "path": String, // The specific API endpoint path (e.g., "/v1/models/gemini-pro:generateContent")
    "headers": Object, // Key-value pairs of request headers
    "body": Object // The full JSON body of the request
  },
  "response": {
    "status": Integer, // HTTP status code (e.g., 200)
    "headers": Object, // Key-value pairs of response headers
    "body": Object // The full JSON body of the response (for non-streaming) or the accumulated body (for streaming)
  },
  "request_duration_ms": Integer, // Duration of the request to the Gemini API in milliseconds
  "generation_settings": Object, // Extracted generation settings from the request body
  "usage_metadata": Object, // Any usage information provided in the response body
  "error": { // Optional field to log errors
    "message": String,
    "details": Object
  }
}
```

*   For streaming responses, the `response.body` field will be populated with the complete accumulated response after the stream is finished.
*   The `generation_settings` and `usage_metadata` fields will be extracted from the request and response bodies respectively for easier querying and analysis.

## 5. Architecture Design

The application will follow a simple proxy pattern.

```mermaid
graph LR
    Client --> Proxy (FastAPI Application)
    Proxy --> Gemini API
    Gemini API --> Proxy
    Proxy --> Database (MongoDB)
    Proxy --> Client
```

**Components:**

*   **FastAPI Application:** This will be the core of the proxy. It will define routes that mirror the expected Gemini API endpoints.
*   **HTTP Client:** A library within the FastAPI application (e.g., `httpx`) will be used to forward requests to the Gemini API and handle responses, including streaming.
*   **MongoDB Client:** A library within the FastAPI application (e.g., `pymongo`) will be used to connect to the MongoDB database and insert the logged data.
*   **Docker Container:** The FastAPI application and its dependencies will be packaged into a Docker image and run as a container.
*   **MongoDB Container:** A separate Docker container will run the MongoDB database. A Docker volume will be used to persist the database data.

**Flow:**

1.  A client (VS Code extension) sends an HTTP request to the proxy's address and port.
2.  The FastAPI application receives the request.
3.  The proxy logs the incoming request details (method, path, headers, body).
4.  The proxy forwards the request to the appropriate Gemini API endpoint using the HTTP client.
5.  The proxy receives the response from the Gemini API.
6.  If the response is streaming, the proxy will stream it back to the client while accumulating the full response body.
7.  Once the full response is received (either directly or after streaming), the proxy logs the response details (status, headers, body, duration, settings, usage metadata) to the MongoDB database.
8.  The proxy sends the response back to the original client.
9.  If errors occur at any stage, they are caught and logged in the database.

## 6. Future Considerations

*   **Authentication/Authorization:** For multi-user scenarios or external access, consider adding authentication and authorization layers to the proxy.
*   **Multiple Providers:** Design the database schema and proxy logic to easily accommodate logging interactions with other AI model providers.
*   **Analytics Dashboard:** Develop a separate application or use a tool to query and visualize the data stored in MongoDB for usage analytics.
*   **Data Export:** Implement functionality to export data from MongoDB for finetuning purposes.

This SRS and architecture design provide a foundation for building the Gemini API proxy. The next steps involve implementing the FastAPI application, setting up the Docker environment, and writing the necessary code for request handling, logging, and database interaction.
