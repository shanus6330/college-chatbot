from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load the Excel file
data = pd.read_excel("cres_data_cleaned.xlsx")
print("COLUMNS:", data.columns.tolist())  # should print your column names

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Read the message from the JSON POST payload
        user_message = request.json["message"].lower()

        # If the message asks about subjects:
        if "subject" in user_message:
            # Use the correct column name from your Excel file
            subjects = data["subject name"].dropna().unique().tolist()
            return jsonify({"response": "Subjects offered: " + ", ".join(subjects)})

        # If the message asks about faculty:
        elif "faculty" in user_message:
            faculties = data["faculty name"].dropna().unique().tolist()
            return jsonify({"response": "Faculty members are: " + ", ".join(faculties)})

        # If the message asks about credits:
        elif "credit" in user_message:
            avg_credit = data["credits"].mean()
            return jsonify({"response": f"The average credit is {avg_credit:.2f}"})

        # If nothing matches:
        else:
            return jsonify({"response": "Sorry, I didn’t understand that. Try asking about subjects, faculty, or credits."})

    except Exception as e:
        # Print error details to the terminal for debugging.
        print("ERROR:", e)
        return jsonify({"response": "Server error occurred."}), 500

if __name__ == "__main__":
    app.run(debug=True)
