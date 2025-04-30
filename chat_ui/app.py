import os
import sys
import re
import random

# ensure project root on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, request, jsonify, render_template
from common.db_client import DBClient
from common.spell_corrector import SpellCorrector
from common.paraphraser import Paraphraser
from common.config import TOP_K, FIDELITY_THRESH

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

db = DBClient()
speller = SpellCorrector()
paraphraser = Paraphraser()

# Define greeting patterns and responses
def is_greeting(message):
    # Convert to lowercase for case-insensitive matching
    msg = message.lower()

    # English greetings
    english_greetings = [
        r'\b(hi|hello|hey|greetings|howdy)\b',
        r'\bgood\s*(morning|afternoon|evening|day)\b',
        r'\bhow\s*(are\s*you|is\s*it\s*going|are\s*things)\b',
        r'\bwhat[\'\']*s\s*up\b',
        r'\bnice\s*to\s*(meet|see)\s*you\b'
    ]

    # Hindi greetings
    hindi_greetings = [
        r'\b(namaste|namaskar|नमस्ते|नमस्कार)\b',
        r'\b(kaise\s*ho|कैसे\s*हो)\b',
        r'\b(aap\s*kaise\s*hain|आप\s*कैसे\s*हैं)\b',
        r'\b(shubh\s*din|शुभ\s*दिन)\b',
        r'\b(suprabhat|सुप्रभात)\b',
        r'\b(shubh\s*prabhat|शुभ\s*प्रभात)\b'
    ]

    # Thank you expressions
    thank_you = [
        r'\b(thank\s*you|thanks|thank\s*you\s*very\s*much|thanks\s*a\s*lot)\b',
        r'\b(dhanyavaad|धन्यवाद|shukriya|शुक्रिया)\b'
    ]
    
    # Basic acknowledgments and short responses
    acknowledgments = [
        r'\b(okay|ok|k|sure|alright|fine|got\s*it|understood|i\s*see)\b',
        r'\b(yes|no|maybe|perhaps|probably)\b',
        r'\b(cool|great|awesome|nice|good|excellent|perfect)\b'
    ]

    # Check if message matches any greeting pattern
    for pattern in english_greetings + hindi_greetings:
        if re.search(pattern, msg):
            return "greeting"

    for pattern in thank_you:
        if re.search(pattern, msg):
            return "thanks"
            
    for pattern in acknowledgments:
        if re.search(pattern, msg):
            return "acknowledgment"

    return None

def get_greeting_response(greeting_type, msg):
    # For greetings, respond with the same greeting and then add information about the school
    if greeting_type == "greeting":
        # Check which greeting was used and respond with the same
        msg_lower = msg.lower()

        if re.search(r'\b(namaste|namaskar|नमस्ते|नमस्कार)\b', msg_lower):
            return "Namaste! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\b(kaise\s*ho|कैसे\s*हो|aap\s*kaise\s*hain|आप\s*कैसे\s*हैं)\b', msg_lower):
            return "Main badiya hoon! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\bgood\s*morning\b', msg_lower):
            return "Good morning! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\bgood\s*afternoon\b', msg_lower):
            return "Good afternoon! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\bgood\s*evening\b', msg_lower):
            return "Good evening! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\b(hi|hello)\b', msg_lower):
            return "Hi! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        elif re.search(r'\bhey\b', msg_lower):
            return "Hey there! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

        # Default greeting response
        return "Hello! I am a chatbot for G.D. Goenka Public School, Vasant Kunj. You can ask me any questions about our school."

    elif greeting_type == "thanks":
        return "You're welcome! I am here to help with any questions about G.D. Goenka Public School, Vasant Kunj."
        
    elif greeting_type == "acknowledgment":
        msg_lower = msg.lower()
        
        if re.search(r'\b(okay|ok|k|sure|alright|fine|got\s*it|understood|i\s*see)\b', msg_lower):
            return "Great! Is there anything specific about G.D. Goenka Public School you'd like to know about?"
            
        elif re.search(r'\b(yes)\b', msg_lower):
            return "Wonderful! Please go ahead and ask your question about our school."
            
        elif re.search(r'\b(no)\b', msg_lower):
            return "Alright. If you have any questions about G.D. Goenka Public School in the future, feel free to ask."
            
        elif re.search(r'\b(cool|great|awesome|nice|good|excellent|perfect)\b', msg_lower):
            return "I'm glad to hear that! What else would you like to know about G.D. Goenka Public School?"
            
        # Default acknowledgment response
        return "I understand. Is there anything specific about G.D. Goenka Public School you'd like to know?"

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"error": "empty message"}), 400

    # Check if the message is a greeting or thank you
    greeting_type = is_greeting(msg)
    if greeting_type:
        # Return a custom greeting response
        return jsonify({
            "question": msg,
            "corrected_query": msg,  # No need to correct greetings
            "answer": get_greeting_response(greeting_type, msg),
            "distance": 0.0,  # Perfect match
            "source": "Greeting Handler"
        })
        
    # Handle single-word queries for "class" and "fees"
    msg_lower = msg.lower()
    words = msg_lower.split()
    
    # Check if it's a single word query for "class" or "fees" without numbers
    if len(words) == 1:
        if words[0] == "class" or words[0] == "classes":
            return jsonify({
                "question": msg,
                "corrected_query": msg,
                "answer": "Which class are you interested in knowing about? We have classes from Nursery to Class 12 at G.D. Goenka Public School.",
                "distance": 0.0,
                "source": "Single Word Handler",
                "below_threshold": False
            })
        elif words[0] == "fee" or words[0] == "fees":
            return jsonify({
                "question": msg,
                "corrected_query": msg,
                "answer": "For which class would you like to know the fee structure? Please specify the class or grade level you're interested in.",
                "distance": 0.0,
                "source": "Single Word Handler",
                "below_threshold": False
            })
    
    # Check if query contains only "class" or "fees" with numbers but no other context
    if len(words) == 2 and any(word.isdigit() for word in words):
        if "class" in words or "classes" in words:
            class_num = next((word for word in words if word.isdigit()), None)
            if class_num:
                # Let this continue to normal processing as it has enough context
                pass
        elif "fee" in words or "fees" in words:
            class_num = next((word for word in words if word.isdigit()), None)
            if class_num:
                # Let this continue to normal processing as it has enough context
                pass

    # 1) Spell‐correct the input
    corrected = speller.correct(msg)

    # 2) Semantic search on corrected query
    col = db.get_or_create_collection("delhi")
    results = col.query(
        query_texts=[corrected],
        n_results=TOP_K,
        include=["metadatas", "distances"]
    )

    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # 3) If NO hits or best hit doesn't meet threshold, fallback
    if not metadatas or distances[0] > FIDELITY_THRESH:
        return jsonify({
            "question": msg,
            "corrected_query": corrected,
            "answer": "I'm not confident I have the right information to answer that question. Please try rephrasing or ask me something else about G.D. Goenka Public School.",
            "distance": distances[0] if distances else None,
            "source": "",
            "below_threshold": True
        })

    # 4) Otherwise always answer the top hit
    best_meta = metadatas[0]
    best_dist = distances[0]
    answer = best_meta.get("answer", "")

    # 5) Paraphrase for style/tone
    paraphrased = paraphraser.paraphrase(answer)

    return jsonify({
        "question": msg,
        "corrected_query": corrected,
        "answer": paraphrased,
        "distance": best_dist,
        "source": best_meta.get("source", ""),
        "below_threshold": False
    })

if __name__ == "__main__":
    app.run(port=8001, debug=True)

