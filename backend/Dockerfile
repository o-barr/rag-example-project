# Use the official Python image as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the uploaded_files directory and set permissions
RUN mkdir -p /app/uploaded_files && chmod -R 755 /app/uploaded_files

# Expose the port (optional)
EXPOSE 8000

# Run the Flask app
CMD ["python", "main.py"]
