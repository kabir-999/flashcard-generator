import os
import fitz  # PyMuPDF for extracting text from PDFs
import json
from flask import Flask, request, jsonify, render_template
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
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction="Generate concise, structured flashcards from the given content, preserving all key terms."
)

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    
    print("\n📄 Extracted PDF Text (First 500 chars):\n", text[:500])  # Debugging Log
    return text.strip()

# Function to generate flashcards
def generate_flashcards(extracted_text):
    try:
        if not extracted_text.strip():
            return {"error": "PDF text extraction failed or is empty."}

        # Properly formatted prompt for Gemini
        prompt = f"Generate educational flashcards from the following content:\n\n{extracted_text}"
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(prompt)

        print("\n🤖 Raw API Response:\n", response.text)  # Debugging Log

        if not response.text or response.text.strip() == "":
            return {"error": "No flashcards generated. API response empty."}

        # Process response into JSON format
        flashcards = response.text.strip().split("\n\n")
        structured_flashcards = []

        for flashcard in flashcards:
            if "**Front:**" in flashcard and "**Back:**" in flashcard:
                front, back = flashcard.split("**Back:**", 1)
                structured_flashcards.append({
                    "front": front.replace("**Front:**", "").strip(),
                    "back": back.strip()
                })

        # Save flashcards to a JSON file
        with open("flashcards.json", "w", encoding="utf-8") as json_file:
            json.dump({"flashcards": structured_flashcards}, json_file, indent=4)

        return {"flashcards": structured_flashcards}

    except Exception as e:
        print("❌ Error:", str(e))
        return {"error": str(e)}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate_flashcards_api():
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

        flashcards_json = generate_flashcards(extracted_text)
        return jsonify(flashcards_json)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
