from flask import Flask, render_template, request, redirect, session, flash
import firebase_admin
from firebase_admin import credentials,auth, firestore
import os, json
import requests


app=Flask(__name__)

app.secret_key="secret_key"


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
#firebase initilization

firebase_key = os.getenv("FIREBASE_KEY")

if firebase_key:
    firebase_dict = json.loads(firebase_key)
    cred = credentials.Certificate(firebase_dict)
else:
    cred = credentials.Certificate("firebase_key1.json")

firebase_admin.initialize_app(cred)
# if os.getenv('FIREBASE_KEY'):
#     firebase_key=json.load(os.environ["FIREBASE_KEY"])
#     cred=credentials.Certificate("firebase_key")
#
# else:
#     cred=credentials.Certificate("firebase_key1.json")
#
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)

db=firestore.client()

@app.route("/")
def home():

    chat_history = []
    chats = []
    current_chat = session.get("current_chat")

    if "user_id" in session:

        user_id = session["user_id"]

        # get all chats for this user
        chat_docs = db.collection("chats").where("user_id", "==", user_id).stream()

        chats = [chat.id for chat in chat_docs]

    if current_chat:
        chat_ref = db.collection('chats').document(current_chat)
        chat_doc = chat_ref.get()

        if chat_doc.exists:
            chat_history = chat_doc.to_dict().get('messages', [])

    return render_template(
        "index.html",
        logged_in=("user_id" in session),
        chats=chats,
        current_chat=current_chat,
        chat_history=chat_history
    )


@app.route("/signup",methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        
        try:
            user=auth.create_user(email=email,password=password)
            session['user_id']=user.uid
            return redirect("/")
        except auth.EmailAlreadyExistsError:
            return render_template("signup.html",error= "email already exists")
        
    return render_template("signup.html")


@app.route("/login",methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        

        try:
            user=auth.get_user_by_email(email)
            session['user_id']=user.uid
            chat_ref=db.collection("chats").document()
            chat_ref.set({
                "user_id":user.uid,
                "title":"New chat",
                "messages": [],
            })

            session['current_chat']=chat_ref.id

            return redirect("/")
        
        except:
            return render_template("login.html",error="user not found")
        
    return render_template("login.html")
        

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")

# @app.route("/chat",methods=['POST'])
# def chat():
#     if 'user_id' not in session:
#         flash("Please login or signup to continue chatting with Mindmate.")
#         return redirect("/login")
#     if "chats" not in session:
#         session['chats']={}
#
#     # if 'current_chat' not in session:
#     #     chat_id="chat1"
#     #     session["current_chat"] = chat_id
#     #     session["chats"][chat_id] = []
#     # chat_id = session["current_chat"]
#
#     if 'current_chat' not in session:
#         chat_ref=db.collection("chats").document()
#
#         chat_ref.set({
#             "user_id":session['user_id'],
#             'messages':[]
#
#         })
#
#         session['current_chat']=chat_ref.id
#
#     else:
#         chat_id=session['current_chat']
#         chat_ref=db.collection('chats').document(chat_id)
#
#     # if "chat_history" not in session:
#     #     session['chat_history']=[]
#
#     user_message=request.form['message']
#     chat_id=session['current_chat']
#     chat_ref=db.collection('chats').document(chat_id)
#     chat_doc=chat_ref.get()
#     if chat_doc.exists:
#
#         messages=chat_doc.to_dict().get('messages',[])
#     else:
#         messages=[]
#
#     messages.append({
#         "role":'user',
#         'content':user_message
#     })
#
#     chat_ref.set({
#         'user_d':session['user_id'],
#             'messages':messages
#     })
#     # session['chats'][chat_id].append({
#     #     "role":'user',
#     #     "content":user_message
#     # })
#     # session['chat_history'].append({
#     #     'role':"user",
#     #     'content':user_message
#     # })
#
#     # ai_reply="i understand your feelings just calm down"
#     headers={'Authorization':f'Bearer {OPENROUTER_API_KEY}',
#              'Content-type':"application/json",
#              "HTTP-Referer": "http://localhost:5000",
#         "X-Title": "MindMate"}
#     json={
#         "model": "meta-llama/llama-3.1-8b-instruct",
#         "max_tokens": 200,
#         "messages": [
#             {
#                 "role": "system",
#                 "content": """
#                             You are MindMate, a warm and emotionally intelligent AI companion.
#
#                             Speak like a real supportive friend — natural, conversational, and human.
#                             Do NOT sound like a therapist template.
#                             Do NOT repeat phrases like "I'm here to support you" in every reply.
#                             Avoid reintroducing yourself.
#                             Keep responses concise but meaningful (3–6 sentences max).
#
#                             Respond directly to the user's exact situation.
#                             Acknowledge their specific struggles.
#                             Offer gentle reflection or one thoughtful question.
#
#                             Be relatable. Be calm. Be real.
#                             """
#                     }
#         ] + messages
#     }
#
#     response=requests.post(url="https://openrouter.ai/api/v1/chat/completions",headers=headers,json=json)
#     data=response.json()
#     print(data)
#     try:
#         ai_reply = data["choices"][0]["message"]["content"]
#     except KeyError:
#         ai_reply = "Error from AI: " + str(data)
#     # session['chats'][chat_id].append({
#     #     "role":"assistant",
#     #     "content":ai_reply
#     # })
#     messages.append({
#         "role":'assistant',
#         "content":ai_reply
#     })
#
#     chat_ref.update({
#         "messages":messages
#     })
#
#     session.modified=True
#
#     return redirect("/")

@app.route("/chat",methods=['POST'])
def chat():

    if 'user_id' not in session:
        flash("Please login or signup to continue chatting with Mindmate.")
        return redirect("/login")

    # get current chat id
    chat_id = session.get("current_chat")

    # if no chat exists create one
    if not chat_id:
        chat_ref = db.collection("chats").document()
        chat_ref.set({
            "user_id": session['user_id'],
            "messages": []
        })
        chat_id = chat_ref.id
        session['current_chat'] = chat_id

    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if chat_doc.exists:
        messages = chat_doc.to_dict().get('messages', [])
    else:
        messages = []

    user_message = request.form['message']

    messages.append({
        "role": "user",
        "content": user_message
    })

    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-type': "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "MindMate"
    }

    json_data = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "max_tokens": 200,
        "messages": [
            {
                "role": "system",
                "content": """
You are MindMate, a warm and emotionally intelligent AI companion.

Speak like a real supportive friend — natural, conversational, and human.
Do NOT sound like a therapist template.
Keep responses concise but meaningful.
"""
            }
        ] + messages
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=json_data
    )

    data = response.json()

    try:
        ai_reply = data["choices"][0]["message"]["content"]
    except:
        ai_reply = "AI response error"

    messages.append({
        "role": "assistant",
        "content": ai_reply
    })

    chat_ref.update({
        "user_id": session['user_id'],
        "messages": messages
    })

    session.modified = True

    return redirect("/")
@app.route("/new_chat")
def new_chat():
    # session.pop("chat_history",[])
    # if "chats" not in session:
    #     session['chats']={}
    # chat_id=f"chat{len(session['chats'])+1}"
    # session['chats'][chat_id]=[]
    # session["current_chat"] = chat_id

    # session.modified = True
    # return redirect("/")
    if "user_id" not in session:
        return redirect("/login")
    user_id=session['user_id']

    #create new firbase document
    chat_ref=db.collection("chats").document()

    chat_ref.set(
        {
            "user_id":user_id,
            'messages':[]
        }
    )
    session['current_chat']=chat_ref.id

    return redirect("/")

@app.route("/switch_chat/<chat_id>")
def switch_chat(chat_id):

    # if "chats" in session and chat_id in session["chats"]:
    session["current_chat"] = chat_id

    return redirect("/")


if __name__=="__main__":
    app.run(debug=True)