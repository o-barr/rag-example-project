
# Retrieval-Augmented Generation (RAG) – React and Flask Application with OpenAI Integration

This project is a full-stack application that allows users to upload PDF documents, process them using OpenAI's embeddings, and ask questions about the uploaded documents. The application consists of a React frontend and a Flask backend, orchestrated using Docker Compose. 


## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Additional Notes](#additional-notes)
- [License](#license)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose)
- An OpenAI API key (you can obtain one from [OpenAI](https://platform.openai.com/signup/))

## Project Structure

```
├── backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── frontend
│   ├── Dockerfile
│   ├── package.json
│   └── src
│       └── App.js
├── docker-compose.yml
└── README.md
```

- **backend/**: Contains the Flask backend application.
- **frontend/**: Contains the React frontend application.
- **docker-compose.yml**: Defines services for Docker Compose.
- **README.md**: Documentation for the project.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/o-barr/rag-example-project.git
cd rag-example-project
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory of the project and add:
- your OpenAI API key 
- the URL where the frontend can reach the backend (http://localhost:8000 if running locally)

```env
OPENAI_API_KEY=your_openai_api_key
REACT_APP_BACKEND_URL=http://replace-with-your-url:8000
```

### 3. Configure Docker File Sharing (macOS and Windows Users)

For macOS and Windows users, ensure Docker Desktop has access to your project directory:

1. Open **Docker Desktop**.
2. Go to **Preferences** > **Resources** > **File Sharing**.
3. Add your project directory (e.g., `/Users/yourusername/rag-example-project`).
4. Click **Apply & Restart**.

## Running the Application

### 1. Build and Start the Containers

In the root directory of the project, run:

```bash
docker-compose up --build
```

This command will build the Docker images for both the frontend and backend services and start the containers.

### 2. Access the Application

- **Frontend**: Open [http://localhost:3000](http://localhost:3000) in your web browser.
- **Backend API (optional)**: The backend runs on [http://localhost:8000](http://localhost:8000).

## Environment Variables

- **OPENAI_API_KEY**: Your OpenAI API key. Required for the backend to access OpenAI services.
- **REACT_APP_BACKEND_URL**: The URL where the frontend can reach the backend. Set to `http://localhost:8000` by default.

These variables are set in the `.env` file and `docker-compose.yml`.

## Usage

### Uploading a PDF Document

1. On the frontend, click the **"Upload PDF"** button.
2. Select a PDF file from your computer.
3. Wait for the upload and processing to complete.

### Asking Questions

1. After the PDF is processed, enter a question related to the content of the PDF in the input field.
2. Click **"Submit"**.
3. The application will display an answer generated using OpenAI's language model.

## Troubleshooting

### Common Issues and Solutions

#### 1. CORS Errors

**Error Message:**

```
Access to fetch at 'http://localhost:8000/upload' from origin 'http://localhost:3000' has been blocked by CORS policy.
```

**Solution:**

- Ensure that `flask_cors` is installed and properly configured in `main.py`:

  ```python
  from flask_cors import CORS

  app = Flask(__name__)
  CORS(app)
  ```

- Rebuild the backend Docker image:

  ```bash
  docker-compose down
  docker-compose up --build
  ```

#### 2. Backend Fails to Start Due to Volume Mount Errors

**Error Message:**

```
Error response from daemon: invalid mount config for type "bind": stat /host_mnt/...: operation not permitted
```

**Solution:**

- Ensure Docker Desktop has file sharing access to your project directory (see [Installation and Setup](#installation-and-setup)).
- Check directory permissions and ensure Docker has read/write access.

#### 3. Frontend Cannot Reach Backend

**Error Message in Browser Console:**

```
Failed to load resource: net::ERR_NAME_NOT_RESOLVED
```

**Solution:**

- Update `REACT_APP_BACKEND_URL` in `docker-compose.yml` to use `http://localhost:8000`:

  ```yaml
  environment:
    - REACT_APP_BACKEND_URL=http://localhost:8000
  ```

- Rebuild the frontend Docker image:

  ```bash
  docker-compose down
  docker-compose up --build
  ```

#### 4. Missing Dependencies or Module Errors

**Error Message:**

```
ModuleNotFoundError: No module named '...' 
```

**Solution:**

- Ensure all dependencies are listed in `requirements.txt` (backend) or `package.json` (frontend).
- Rebuild the Docker images to install updated dependencies.

#### 5. FAISS Initialization Error

**Error Message:**

```
TypeError: FAISS.__init__() got an unexpected keyword argument 'embeddings'
```

**Solution:**

- Correct the initialization of the FAISS vector store in your `main.py`:

  ```python
  # Remove incorrect initialization
  # vectorstore = FAISS(embeddings=embeddings)

  # Correct usage
  vectorstore = FAISS.from_documents(all_texts, embeddings)
  ```

#### 6. NameError: name 'traceback' is not defined

**Error Message:**

```
NameError: name 'traceback' is not defined
```

**Solution:**

- Import the `traceback` module at the top of your `main.py`:

  ```python
  import traceback
  ```

## Additional Notes

### Docker Compose Configuration

- The `docker-compose.yml` defines two services:
  - **backend**: Runs the Flask application.
  - **frontend**: Runs the React application.
- Ports are mapped as:
  - **Frontend**: `localhost:3000`
  - **Backend**: `localhost:8000`

### OpenAI API Usage

- The application uses OpenAI's embeddings and language models to process documents and generate answers.
- Ensure your OpenAI API key is valid and has sufficient quota.

### File Uploads and Storage

- Uploaded PDF files are stored in the backend container under `/app/uploaded_files`.
- If you need to access uploaded files from the host machine, consider adding a volume mapping.

### Volume Mapping (Optional)

To access uploaded files from your host machine, modify the `docker-compose.yml`:

```yaml
services:
  backend:
    # ... other configurations ...
    volumes:
      - ./uploaded_files:/app/uploaded_files
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
