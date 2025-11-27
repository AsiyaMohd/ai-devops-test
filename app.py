from flask import Flask, render_template_string, jsonify
import random

app = Flask(__name__)

# ---------------------------------------------------------
# Data Source (In a real app, this might come from a DB)
# ---------------------------------------------------------
wisdom_quotes = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "It does not matter how slowly you go as long as you do not stop. - Confucius",
    "In the middle of every difficulty lies opportunity. - Albert Einstein",
    "Happiness is not something ready made. It comes from your own actions. - Dalai Lama",
    "Turn your wounds into wisdom. - Oprah Winfrey",
    "Simplicity is the ultimate sophistication. - Leonardo da Vinci",
    "Everything you can imagine is real. - Pablo Picasso"
]

# ---------------------------------------------------------
# HTML Template (Embedded for single-file simplicity)
# ---------------------------------------------------------
# Usually, this goes into a 'templates/index.html' file.
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Wisdom</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }
        h1 { color: #333; margin-bottom: 1.5rem; }
        p { font-size: 1.2rem; color: #555; line-height: 1.6; min-height: 80px; }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 1rem;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <div class="card">
        <h1>💡 Daily Wisdom</h1>
        <p id="quote-box">{{ initial_quote }}</p>
        <button onclick="getNewQuote()">Get New Quote</button>
    </div>

    <script>
        async function getNewQuote() {
            const quoteBox = document.getElementById('quote-box');
            quoteBox.style.opacity = 0; // Fade out effect
            
            try {
                const response = await fetch('/api/quote');
                const data = await response.json();
                
                setTimeout(() => {
                    quoteBox.innerText = data.quote;
                    quoteBox.style.opacity = 1; // Fade in
                }, 300);
            } catch (error) {
                console.error('Error fetching quote:', error);
                quoteBox.innerText = "Failed to load wisdom. Try again!";
                quoteBox.style.opacity = 1;
            }
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.route('/')
def home():
    """Renders the main page with an initial random quote."""
    return render_template_string(html_template, initial_quote=random.choice(wisdom_quotes))

@app.route('/api/quote')
def get_quote():
    """API Endpoint to return a random quote as JSON."""
    return jsonify({'quote': random.choice(wisdom_quotes)})

# ---------------------------------------------------------
# Run the App
# ---------------------------------------------------------
if __name__ == '__main__':
    print("Starting Flask server...")
    print("Go to http://127.0.0.1:5000/ in your browser")
    app.run(host='0.0.0.0',debug=True, port=5000)