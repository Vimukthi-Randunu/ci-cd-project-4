from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, this is Project 4 running in Docker!"

if __name__ == "__main__":
    app.run(debug=True)