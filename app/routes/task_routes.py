from ast import If

from flask import Blueprint, jsonify
from flask import Response
from app.models.task import Task
from app.models.goal import Goal
from ..db import db
from flask import request
from datetime import datetime, timezone
import os
import requests
from .route_utilities import validate_model, create_model

task_bp = Blueprint("task_bp", __name__)

#route helper method to retrieve model by id, returns None if not found
def get_task_by_id(task_id):
    query = db.select(Task).where(Task.id == task_id)
    task = db.session.scalar(query)

    return task

@task_bp.get("/tasks") # Handles GET requests to /tasks
def get_all_tasks():

    sort_param = request.args.get("sort")

    query = db.select(Task) 

    # Wave 2 - Sort tasks by title
    if sort_param == "asc":
        query = query.order_by(Task.title.asc())
    elif sort_param == "desc":
        query = query.order_by(Task.title.desc())
    else:
        query = query.order_by(Task.id)
    
    tasks = db.session.scalars(query).all() 
    return [task.to_dict() for task in tasks], 200 

@task_bp.get("/tasks/<int:task_id>") #dynamic URL parameter.
def get_task(task_id):
    task = validate_model(Task, task_id)
    return task.to_dict(), 200

@task_bp.post("/tasks") # Handles POST requests to /tasks
def create_task():
    request_body = request.get_json(silent=True)

    return create_model(Task, request_body)
    
@task_bp.put("/tasks/<int:task_id>") # Handles PUT requests to /tasks/<task_id>
def update_task(task_id):
    task = validate_model(Task, task_id)

    if task is None:
        return {"details": "Task not found"}, 404

    task_data = request.get_json() 

    try:
        title = task_data["title"]
        description = task_data["description"]
    except (KeyError, TypeError):
        return {"details": "Invalid data"}, 400

    task.title = title
    task.description = description

    db.session.commit()

    return Response(status=204, mimetype="application/json")


@task_bp.delete("/tasks/<int:task_id>") # Handles DELETE requests to /tasks/<task_id>
def delete_task(task_id):
    task = validate_model(Task, task_id)

    db.session.delete(task)
    db.session.commit()

    return Response(status=204, mimetype="application/json")


#wave 3
@task_bp.patch("/tasks/<int:task_id>/mark_complete")
def mark_complete(task_id):
    task = validate_model(Task, task_id)

    # If completed_at = None → assigns the current datetime.
    # If completed_at already has a datetime → replaces it with the current datetime.
    task.completed_at = datetime.now(timezone.utc)

    db.session.commit()

    #wave 4: 
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_channel = os.environ.get("SLACK_CHANNEL")

    # Send notification
    if slack_token and slack_channel:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {slack_token}"
            },
            json={
                "channel": slack_channel,
                "text": f"Someone just completed the task {task.title}"
            },
            timeout=10
        )

    return "", 204

@task_bp.patch("/tasks/<int:task_id>/mark_incomplete")
def mark_incomplete(task_id):
    task = validate_model(Task, task_id)

    #this makes is_complete return False when to_dict() is called
    task.completed_at = None
    db.session.commit()

    return "", 204

