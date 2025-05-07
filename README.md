# Gemini API Caching Proxy

This project implements a local proxy for the Gemini API. It intercepts requests from clients, logs them to a MongoDB database, and forwards the responses back to the client. This is particularly useful for applications like VS Code extensions that interact with the Gemini API, allowing for logging and analysis of API interactions.

## Features

*   **Request and Response Logging:** Logs full request and response data, including headers, body, status codes, and timing.
*   **Streaming Support:** Handles and logs streaming responses from the Gemini API.
*   **MongoDB Storage:** Stores logged data in a MongoDB database, capable of handling large volumes of data.
*   **Dockerized:** Easy to set up and run locally using Docker and Docker Compose.
*   **Extensible:** Designed to potentially support other AI service providers in the future.

## Architecture

The proxy follows a simple proxy pattern:
```mermaid
flowchart TD
    Client(["Client"]) --> Proxy["Proxy [FastAPI Application]"]
    Proxy --> GeminiAPI["Gemini API"]
    GeminiAPI --> Proxy
    Proxy --> Database["Database [MongoDB]"]
    Proxy --> Client
```

The main components are:

*   **FastAPI Application:** The core proxy logic, handling request interception, forwarding, and response logging.
*   **HTTP Client:** Used for forwarding requests to the Gemini API.
*   **MongoDB Client:** Used for interacting with the MongoDB database.
*   **Docker Containers:** The FastAPI application and MongoDB are run as separate Docker containers managed by Docker Compose.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:raslab/gemini_caching_proxy.git
    cd gemini_caching_proxy
    ```

2.  **Set up environment variables:**
    Copy the `.env.example` file to `.env` and update the `GEMINI_API_KEY` with your actual Gemini API key.
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file:
    ```
    GEMINI_API_KEY=YOUR_GEMINI_API_KEY
    ```

3.  **Run with Docker Compose:**
    Build and run the Docker containers using Docker Compose.
    ```bash
    docker-compose up --build -d
    ```
    This will start the FastAPI proxy application and the MongoDB database in detached mode.

## Usage

Once the Docker containers are running, configure your client application (e.g., VS Code extension) to send requests to the proxy's address and port (default is `http://localhost:8000`). The proxy will then handle the forwarding and logging.

## Database

The logged data is stored in a MongoDB database. The database data is persisted using a Docker volume. You can connect to the MongoDB container to view or analyze the logged interactions in the `gemini_interactions` collection.

## Future Enhancements

*   Authentication and authorization layers.
*   Support for other AI model providers.
*   Analytics dashboard for visualizing usage patterns.
*   Data export functionality for finetuning.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

[Include license information here, e.g., link to a LICENSE file]
