import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

with open("data.json", "r") as f:
    data_structure = json.load(f)

app = FastAPI(
    title="Student chat data API",
    description=(
        "A small API for looking up student chat data and usage. "
        "Open `/docs` while the server is running to try each route."
    ),
)

origins = ["http://localhost:5001", "http://127.0.0.1:5001"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Allows requests from these origins
    allow_credentials=True,         # Allows cookies/auth headers
    allow_methods=["*"],            # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],            # Allows all request headers
)

@app.get(
    "/",
    summary="Check that the API is running",
    description="Returns a short welcome message. Use this as a quick health check.",
)
def index():
    """Return a simple message to confirm that the backend is available."""
    return {"message": "Welcome to the FastAPI backend!"}

@app.get(
    "/data",
    summary="Get all stored data",
    description=(
        "Returns the complete data set, including settings and every student. "
        "This is useful for inspecting the raw data, but it can be a large response."
    ),
)
def get_data():
    """Return the full contents of `data_structure.json`."""
    return data_structure

@app.post(
    "/data",
    summary="Update stored data",
    description=(
        "Sends new JSON data to the backend. Any top-level fields in the request "
        "replace fields with the same name in the current data, then the updated data "
        "is saved to `data_structure.json`."
    ),
)
def post_data(new_data: dict):
    """Merge the supplied top-level data into the saved data file."""
    data_structure.update(new_data)
    with open("data_structure.json", "w") as f:
        json.dump(data_structure, f)
    return {"message": "Data updated successfully"}

@app.get(
    "/student/get_id/{user_name}",
    summary="Find a student ID from a username",
    description=(
        "Put the student's username in the URL, for example `/student/get_id/john.smith`. "
        "Returns the student's numeric ID, or a 404 error if no matching username exists."
    ),
)
def get_student_id(user_name: str):
    """Look through the students and return the ID for one username."""
    for student in data_structure.get("students", []):
        if student.get("user_name") == user_name:
            return {"student_id": student.get("id")}
    raise HTTPException(status_code=404, detail="Student username not found")

@app.get(
    "/student/{id}/chat_categories",
    summary="Count a student's chats by category",
    description=(
        "Put a student ID in the URL. The response lists each chat category and how many "
        "of that student's chats belong to it."
    ),
)
def get_student_chat_categories(id: int):
    """Count this student's chats, grouped by their category."""
    for student in data_structure.get("students", []):
        if student.get("id") == id:
            categories = {}
            for chat in student.get("chats"):
                if chat.get("chat_category") not in categories:
                    categories[chat.get("chat_category")] = 1
                else:
                    categories[chat.get("chat_category")] += 1
            return {"chat_categories": categories}
    raise HTTPException(status_code=404, detail="Student ID not found")

@app.get(
    "/student/{id}/usage",
    summary="Get a student's token use and estimated cost",
    description=(
        "Adds up tokens across all of a student's chats and estimates the cost using the "
        "price for each model. It also separates messages written by the student and the AI. "
        "`raw_average` is the average number of tokens per message."
    ),
)
def get_student_usage(id: int):
    """Calculate overall token use, estimated cost, and message averages for one student."""
    for student in data_structure.get("students", []):
        if student.get("id") == id:
            usage = {
                "raw_tokens": 0,
                "cost": 0,
                "user": {"all": [], "raw_average": 0},
                "assistant": {"all": [], "raw_average": 0},
            }
            models = data_structure.get("config", {}).get("models", {})
            for chat in student.get("chats"):
                cost_per_token = models.get(chat.get("model"), {}).get("cost", 0)
                for message in chat.get("content"):
                    tokens = message.get("tokens", 0)
                    usage["raw_tokens"] += tokens
                    usage["cost"] += tokens * cost_per_token
                    token_usage = {
                        "tokens": tokens,
                        "datetime": message.get("datetime"),
                    }
                    if message.get("role") == "user":
                        usage["user"]["all"].append(token_usage)
                    elif message.get("role") == "assistant":
                        usage["assistant"]["all"].append(token_usage)

            usage["user"]["raw_average"] = sum(item["tokens"] for item in usage["user"]["all"]) / len(usage["user"]["all"]) if usage["user"]["all"] else 0
            usage["assistant"]["raw_average"] = sum(item["tokens"] for item in usage["assistant"]["all"]) / len(usage["assistant"]["all"]) if usage["assistant"]["all"] else 0

            return {"usage": usage}
    raise HTTPException(status_code=404, detail="Student ID not found")

@app.get(
    "/student/{id}/chat_categories/usage",
    summary="Compare token use across chat categories",
    description=(
        "Groups one student's message token counts by chat category and by who sent the "
        "message (`user` or `assistant`). `all` contains every count and `raw_average` "
        "is the average count for that group."
    ),
)
def get_student_chat_categories_usage(id: int):
    """Group one student's message token counts by chat category."""
    for student in data_structure.get("students", []):
        if student.get("id") == id:
            categories_usage = {}
            for chat in student.get("chats"):
                category = chat.get("chat_category")
                if category not in categories_usage:
                    categories_usage[category] = {"user": {"all": [], "raw_average": 0}, "assistant": {"all": [], "raw_average": 0}}

                for message in chat.get("content"):
                    if message.get("role") == "user":
                        categories_usage[category]["user"]["all"].append(message["tokens"])
                    elif message.get("role") == "assistant":
                        categories_usage[category]["assistant"]["all"].append(message["tokens"])

            for category, usage in categories_usage.items():
                usage["user"]["raw_average"] = sum(usage["user"]["all"]) / len(usage["user"]["all"]) if usage["user"]["all"] else 0
                usage["assistant"]["raw_average"] = sum(usage["assistant"]["all"]) / len(usage["assistant"]["all"]) if usage["assistant"]["all"] else 0

            return {"chat_categories_usage": categories_usage}
    raise HTTPException(status_code=404, detail="Student ID not found")

@app.get(
    "/student/{id}/models/usage",
    summary="Compare token use across AI models",
    description=(
        "Groups one student's message token counts by the AI model used for each chat. "
        "The result separates student and AI messages and includes an average for each."
    ),
)
def get_student_models_usage(id: int):
    """Group one student's message token counts by the AI model used."""
    for student in data_structure.get("students", []):
        if student.get("id") == id:
            models_usage = {}
            for chat in student.get("chats"):
                model = chat.get("model")
                if model not in models_usage:
                    models_usage[model] = {"user": {"all": [], "raw_average": 0}, "assistant": {"all": [], "raw_average": 0}}

                for message in chat.get("content"):
                    if message.get("role") == "user":
                        models_usage[model]["user"]["all"].append(message["tokens"])
                    elif message.get("role") == "assistant":
                        models_usage[model]["assistant"]["all"].append(message["tokens"])

            for model, usage in models_usage.items():
                usage["user"]["raw_average"] = sum(usage["user"]["all"]) / len(usage["user"]["all"]) if usage["user"]["all"] else 0
                usage["assistant"]["raw_average"] = sum(usage["assistant"]["all"]) / len(usage["assistant"]["all"]) if usage["assistant"]["all"] else 0

            return {"models_usage": models_usage}
    raise HTTPException(status_code=404, detail="Student ID not found")

@app.get(
    "/student/{id}/models/chat_categories",
    summary="Count chat categories for each AI model",
    description=(
        "Shows how many chats a student has in each category for every AI model they used. "
        "For example, it can show how many `basic` chats were maths chats."
    ),
)
def get_student_models_chat_categories(id: int):
    """Count this student's chat categories within each AI model."""
    for student in data_structure.get("students", []):
        if student.get("id") == id:
            models_chat_categories = {}
            for chat in student.get("chats"):
                model = chat.get("model")
                category = chat.get("chat_category")
                if model not in models_chat_categories:
                    models_chat_categories[model] = {}
                if category not in models_chat_categories[model]:
                    models_chat_categories[model][category] = 1
                else:
                    models_chat_categories[model][category] += 1

            return {"models_chat_categories": models_chat_categories}
    raise HTTPException(status_code=404, detail="Student ID not found")

@app.get(
    "/model/{model}/cost",
    summary="Get the price of an AI model",
    description=(
        "Put a model name in the URL, such as `/model/basic/cost`. The response gives the "
        "cost per token, plus easier-to-read costs for one thousand and one million tokens."
    ),
)
def get_cost(model: str):
    """Return the configured token price for one AI model."""
    models = data_structure.get("config", {}).get("models", {})
    if model in models:
        return {
            "cost": models[model]["cost"],
            "cost_thousand_tokens": round(models[model]["cost"]*1000, 4),
            "cost_million_tokens": round(models[model]["cost"]*1000000, 4)
        }
    raise HTTPException(status_code=404, detail="Model not found")

@app.get(
    "/students",
    summary="Get a list of all students",
    description=(
        "Returns a list of all students, including their IDs, usernames and usage data."
        
    )
)
def get_students():
    """Return a list of all students with their IDs, usernames and usage data."""
    students = data_structure.get("students", [])
    return {"students": [{
                "id": student.get("id"),
                "user_name": student.get("user_name"),
                "token_usage": get_student_usage(student.get("id"))["usage"],
                "chat_categories": get_student_chat_categories(student.get("id"))["chat_categories"],
                "chat_categories_usage": get_student_chat_categories_usage(student.get("id"))["chat_categories_usage"],
                "models_usage": get_student_models_usage(student.get("id"))["models_usage"],
                
            } for student in students]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1764)