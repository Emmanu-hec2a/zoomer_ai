from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# Initialize NetMind API
client = OpenAI(
    base_url="https://api.netmind.ai/inference-api/openai/v1",
    api_key=os.getenv("OPEN_API_KEY")
)

# Define FAQ data as a constant
FAQS_DATA = {
    "title": "CenterHelp/Frequently Asked Questions(FAQs)",
    "introduction": (
        "Welcome to the Zoomer Africa Help Center!\n"
        "Here you'll find answers to common questions about our platform. "
        "If you can't find what you're looking for, please don't hesitate to contact our support team."
    ),
    "sections": [
        {
            "title": "Getting Started",
            "questions": [
                {
                    "q": "How do I sign up for Zoomer Africa?",
                    "a": (
                        "You can sign up by clicking the 'Sign Up' button on our homepage or mobile app. "
                        "You'll need to provide your name, email address, and create a password. "
                        "You may also have the option to sign up using your existing Google account."
                    )
                },
                {
                    "q": "Is Zoomer Africa free to use?",
                    "a": (
                        "Yes, Zoomer Africa is free to sign up and use for basic features like connecting with friends, "
                        "sharing updates, and joining communities. We have optional premium features or services for users "
                        "who want to use the platform to its full potential."
                    )
                },
                {
                    "q": "I'm having trouble signing up. What should I do?",
                    "a": (
                        "Please double-check that you've entered your email address correctly and that your password meets "
                        "the requirements. If you're still experiencing issues, please contact our support team through "
                        "the 'Contact Us' page with a description of the problem."
                    )
                }
            ]
        },
        # Additional sections omitted for brevity
    ]
}

@app.route('/faqs', methods=['GET'])
def get_faqs():
    return jsonify(FAQS_DATA)

if __name__ == '__main__':
    app.run(debug=True)
