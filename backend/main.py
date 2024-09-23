from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

# Define the directory where uploaded files will be saved
UPLOAD_FOLDER = "./uploaded_files"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variable for storing the vectorstore
vectorstore = None


# Function to process a PDF document and create vectorized embeddings
def process_document(file_path):
    print(f"Processing PDF: {file_path}")

    # Load the PDF using PyPDFLoader
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Use a text splitter to break down the documents into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    print(f"Document split into {len(texts)} chunks")

    # Use OpenAI embeddings
    embeddings = OpenAIEmbeddings()

    # Store the split documents in a FAISS vector store
    vectorstore = FAISS.from_documents(texts, embeddings)
    return vectorstore


# Route for uploading PDFs
@app.route("/upload", methods=["POST"])
def upload_document():
    global vectorstore
    print("Received a request to upload a file")  # Debug: Request received

    if "file" not in request.files:
        print("No file part in the request")  # Debug: No file in the request
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    print(f"File received: {file.filename}")  # Debug: File received

    if file.filename == "":
        print("No file selected for uploading")  # Debug: No file selected
        return jsonify({"error": "No file selected for uploading"}), 400

    if file and file.filename.endswith(".pdf"):
        # Save the PDF to the upload directory
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
        print(f"File saved to {file_path}")  # Debug: File saved successfully

        # Process the uploaded PDF document for vectorization
        try:
            vectorstore = process_document(file_path)
            print(
                f"PDF processed successfully and vectorized"
            )  # Debug: PDF processing successful
        except Exception as e:
            print(f"Error during PDF processing: {e}")  # Debug: Error in PDF processing
            return jsonify({"error": "PDF processing failed"}), 500

        return (
            jsonify(
                {
                    "message": "PDF uploaded and vectorized successfully!",
                    "file_path": file_path,
                }
            ),
            200,
        )

    print("Invalid file format")  # Debug: Invalid file format
    return jsonify({"error": "Invalid file format. Please upload a PDF file."}), 400


def refine_answer_with_gpt(question, initial_answer):
    # Format the conversation as a chat history
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that provides fluent and accurate responses based on user queries.",
        },
        {"role": "user", "content": f"Question: {question}"},
        {"role": "assistant", "content": f"Answer: {initial_answer}"},
        {"role": "user", "content": "Please provide a fluent and accurate response."},
    ]

    try:
        # Use the updated ChatCompletion method
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, max_tokens=100, temperature=0.7
        )
        # Extract the response from OpenAI
        refined_answer = response.choices[0].message.content
        return refined_answer
    except Exception as e:
        print(f"Error refining answer with GPT: {e}")
        return initial_answer  # Return the original answer if something goes wrong


# Route for asking questions
@app.route("/ask", methods=["POST"])
def ask_question():
    global vectorstore
    data = request.json
    question = data.get("question")

    if not vectorstore:
        return jsonify({"error": "No document uploaded or vectorized yet"}), 400

    # Retrieve the initial answer from the vectorstore
    results = vectorstore.similarity_search(question, k=1)
    if results:
        initial_answer = results[0].page_content
    else:
        return jsonify({"error": "No relevant information found"}), 404

    # Pass the question and initial answer to GPT for refinement
    refined_answer = refine_answer_with_gpt(question, initial_answer)

    return jsonify({"answer": refined_answer}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
