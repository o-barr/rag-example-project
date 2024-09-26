import os
import traceback
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG

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
full_document_text = ""  # Initialize full_document_text



# Function to process a PDF document and create vectorized embeddings
def process_document(file_path):
    global vectorstore, full_document_text  # Include full_document_text
    logging.debug(f"Processing PDF: {file_path}")

    # Load the PDF using PyPDFLoader
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Extract the full document text
    full_document_text = "\n".join([doc.page_content for doc in documents])

    # Define different configurations for chunk sizes and overlaps
    chunk_configs = [
        {"chunk_size": 4000, "chunk_overlap": 400},
        {"chunk_size": 200, "chunk_overlap": 50},
    ]

    # Use OpenAI embeddings
    embeddings = OpenAIEmbeddings()

    # Initialize an empty list to collect all texts
    all_texts = []

    # Process the document for each chunk configuration
    for config in chunk_configs:
        chunk_size = config["chunk_size"]
        chunk_overlap = config["chunk_overlap"]

        # Use a text splitter with the current configuration
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        texts = text_splitter.split_documents(documents)
        logging.debug(
            f"Document split into {len(texts)} chunks with chunk_size {chunk_size} and chunk_overlap {chunk_overlap}"
        )

        # Add metadata to each text indicating the chunk size
        for text in texts:
            if not hasattr(text, "metadata") or text.metadata is None:
                text.metadata = {}
            text.metadata["chunk_size"] = chunk_size

        # Collect all texts
        all_texts.extend(texts)

    # Create the FAISS vector store from the documents
    vectorstore = FAISS.from_documents(all_texts, embeddings)
    logging.info("Created FAISS vector store.")

    return vectorstore


def classify_question(question):
    """
    Classify the question as 'broad' or 'detailed' using OpenAI's API.
    """
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that classifies user questions as 'broad' or 'detailed'. Respond with only 'broad' or 'detailed'.",
        },
        {"role": "user", "content": f"{question}"},
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, temperature=0.0
        )
        answer = response.choices[0].message.content.strip().lower()
        logging.debug(f"Question classified as: {answer}")
        if "broad" in answer:
            return "broad"
        elif "detailed" in answer:
            return "detailed"
        else:
            # Default to detailed if unsure
            return "detailed"
    except Exception as e:
        logging.error(f"Error classifying question: {e}")
        # Default to detailed if error occurs
        return "detailed"


# Route for uploading PDFs
@app.route("/upload", methods=["POST"])
@cross_origin()

def upload_document():
    global vectorstore
    logging.info("Received a request to upload a file")  # Info: Request received

    try:
        if "file" not in request.files:
            logging.warning(
                "No file part in the request"
            )  # Warning: No file in the request
            return jsonify({"error": "No file part in the request"}), 400


        file = request.files["file"]
        logging.info(f"File received: {file.filename}")  # Info: File received

        if file.filename == "":
            logging.warning(
                "No file selected for uploading"
            )  # Warning: No file selected
            return jsonify({"error": "No file selected for uploading"}), 400

        if file and file.filename.endswith(".pdf"):
            # Save the PDF to the upload directory
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)
            logging.info(f"File saved to {file_path}")  # Info: File saved successfully

            # Process the uploaded PDF document for vectorization
            try:
                vectorstore = process_document(file_path)
                logging.info(
                    "PDF processed successfully and vectorized"
                )  # Info: PDF processing successful
            except Exception as e:
                logging.error(
                    f"Error during PDF processing: {e}"
                )  # Error: Error in PDF processing
                traceback.print_exc()
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

        logging.warning("Invalid file format")  # Warning: Invalid file format
        return jsonify({"error": "Invalid file format. Please upload a PDF file."}), 400

    except Exception as e:
        logging.error(f"An error occurred in upload_document: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred"}), 500




def refine_answer_with_gpt(question, initial_answer):
    # Format the conversation as a chat history
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on the provided document excerpt.",
        },
        {
            "role": "user",
            "content": f"Document Excerpt:\n{initial_answer}\n\nQuestion: {question} ",
        },
        {"role": "user", "content": "Please provide a fluent and accurate response."},
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=500,

        )
        refined_answer = response.choices[0].message.content
        logging.debug(f"Refined answer: {refined_answer}")
        return refined_answer
    except Exception as e:
        logging.error(f"Error refining answer with GPT: {e}")
        return initial_answer  # Return the original answer if something goes wrong


def generate_answer_with_full_document(question, full_document_text):
    """
    Generate an answer using the full document text.
    """
    # Optionally limit the document length to avoid exceeding token limits
    MAX_DOCUMENT_CHARACTERS = 8000  # Adjust based on your model's token limit
    if len(full_document_text) > MAX_DOCUMENT_CHARACTERS:
        logging.warning("Document is too long; truncating to fit token limit.")
        full_document_text = full_document_text[:MAX_DOCUMENT_CHARACTERS]

    # Prepare the messages for the OpenAI API
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on the provided document.",
        },
        {
            "role": "user",
            "content": f"Document:\n{full_document_text}\n\nQuestion: {question}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=500,
        )
        answer = response.choices[0].message.content.strip()
        logging.debug(f"Answer generated from full document: {answer}")
        return answer
    except Exception as e:
        logging.error(f"Error generating answer with full document: {e}")
        return "An error occurred while generating the answer."


# Route for asking questions
@app.route("/ask", methods=["POST"])
def ask_question():
    global vectorstore, full_document_text
    data = request.json
    question = data.get("question")

    logging.info(f"Received question: {question}")


    if not vectorstore or not full_document_text:
        logging.warning("No document uploaded or vectorized yet")
        return jsonify({"error": "No document uploaded or vectorized yet"}), 400

    # Classify the question
    question_type = classify_question(question)
    logging.info(f"Question classified as: {question_type}")

    if question_type == "broad":
        # Handle broad questions by evaluating the whole document
        logging.info("Handling as a broad question")
        refined_answer = generate_answer_with_full_document(
            question, full_document_text
        )
    else:
        # Handle detailed questions using vector similarity search
        logging.info("Handling as a detailed question")
        # Retrieve the initial answer from the vectorstore
        results = vectorstore.similarity_search(question, k=2)
        if results:
            initial_answer = results[0].page_content
            logging.debug(f"Initial answer retrieved: {initial_answer}")
        else:
            logging.warning("No relevant information found")
            return jsonify({"error": "No relevant information found"}), 404

        # Pass the question and initial answer to GPT for refinement
        refined_answer = refine_answer_with_gpt(question, initial_answer)
        logging.info("Answer refined and ready to be returned")

    return jsonify({"answer": refined_answer}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
