import os
import fitz  # PyMuPDF for extracting text from PDFs
import time
import json
from flask import Flask, request, Response, render_template, stream_with_context, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Model Configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction="Generate concise, structured flashcards from the given content, preserving all key terms.",
)

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text.strip()

# Streaming Response for Flashcard Generation
def generate_flashcards_stream(extracted_text):
    try:
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(extracted_text)

        if not response.text:
            yield f"data: {json.dumps({'error': 'No flashcards generated.'})}\n\n"
            return

        flashcards = response.text.strip().split("\n\n")

        for flashcard in flashcards:
            if "**Front:**" in flashcard and "**Back:**" in flashcard:
                front, back = flashcard.split("**Back:**", 1)
                front = front.replace("**Front:**", "").strip()
                back = back.strip()

                # Stream front first
                yield f"data: {json.dumps({'front': front})}\n\n"
                time.sleep(3)  # 3-second delay between front & back

                # Stream back after delay
                yield f"data: {json.dumps({'back': back})}\n\n"
                time.sleep(1)  # 1-second delay before next flashcard

    except Exception as e:
        print("❌ Error:", str(e))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_flashcards():
    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    pdf_file = request.files["pdf_file"]

    if pdf_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        # Save PDF temporarily
        pdf_path = "uploaded.pdf"
        pdf_file.save(pdf_path)

        # Extract text from the uploaded PDF
        extracted_text = extract_text_from_pdf(pdf_path)

        if not extracted_text:
            return jsonify({"error": "Could not extract text from the PDF"}), 400

        return Response(stream_with_context(generate_flashcards_stream(extracted_text)), content_type="text/event-stream")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
