from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Webhook is working! You can now use this link in your bot.py"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
