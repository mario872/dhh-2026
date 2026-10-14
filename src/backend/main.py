import json
from fastapi import FastAPI, HTTPException
import uvicorn

with open("data_structure.json", "r") as f:
    data_structure = json.load(f)

app = FastAPI()

@app.get("/")
def index():
    return {"message": "Welcome to the FastAPI backend!"}

@app.get("/data")
def get_data():
    return data_structure

@app.post("/data")
def post_data(new_data: dict):
    data_structure.update(new_data)
    with open("data_structure.json", "w") as f:
        json.dump(data_structure, f)
    return {"message": "Data updated successfully"}

@app.get("/student/get_id/{user_name}")
def get_student_id(user_name: str):
    for student in data_structure.get("students", []):
        if student.get("user_name") == user_name:
            return {"student_id": student.get("id")}
    raise HTTPException(status_code=404, detail="Student username not found")

@app.get("/student/{id}/chat_categories")
def get_student_chat_categories(id: int):
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

@app.get("/student/{id}/usage")
def get_student_usage(id: int):
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

@app.get("/student/{id}/chat_categories/usage")
def get_student_chat_categories_usage(id: int):
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

@app.get("/student/{id}/models/usage")
def get_student_models_usage(id: int):
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

@app.get("/student/{id}/models/chat_categories")
def get_student_models_chat_categories(id: int):
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

@app.get("/model/{model}/cost")
def get_cost(model: str):
    models = data_structure.get("config", {}).get("models", {})
    if model in models:
        return {
            "cost": models[model]["cost"],
            "cost_thousand_tokens": round(models[model]["cost"]*1000, 4),
            "cost_million_tokens": round(models[model]["cost"]*1000000, 4)
        }
    raise HTTPException(status_code=404, detail="Model not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1764)