from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Webhook placeholder is live!"

# DigitalOcean will look for this entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Running on port {port}...")
    app.run(host="0.0.0.0", port=port)


