"""Live chatbot scenario test (needs the backend running and OPEN_ROUTER_API_KEY set).
Uses a fixed "now": Saturday 2026-10-03 10:00, so the coming Tuesday is 2026-10-06.
Run from the repo root: python test_chat_assistant.py"""
import sys, uuid, sqlite3, httpx

B = "http://127.0.0.1:8000"
NOW = "2026-10-03T10:00"
email = f"chat-test-{uuid.uuid4().hex[:8]}@example.com"
token = httpx.post(f"{B}/api/auth/signup", json={"email": email, "password": "test-password-123"}).json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
history = []

def chat(msg):
    r = httpx.post(f"{B}/api/chat/", headers=H, timeout=90,
                   json={"message": msg, "history": history, "client_now": NOW}).json()
    history.extend([{"role": "user", "content": msg}, {"role": "assistant", "content": r["message"]}])
    print(f"> {msg}\n  {r['message']}  {r.get('data')}")

def tasks():
    return httpx.get(f"{B}/api/tasks", headers=H).json()

def show():
    for t in tasks():
        print(f"    - {t['title']!r} due={t['due_date']} {t['due_time']} done={t['completed']}")

failures = []
def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond: failures.append(label)

chat("add a task dentist appointment on coming tuesday at 3pm")
chat("add buy groceries tomorrow")
chat("remind me to call mom")
show()
t = tasks()
check(len(t) == 3, "3 tasks, no duplicates")
d = next((x for x in t if "dentist" in x["title"].lower()), None)
check(d and d["due_date"] == "2026-10-06" and d["due_time"] == "15:00", "dentist on Tue 2026-10-06 15:00")
g = next((x for x in t if "grocer" in x["title"].lower()), None)
check(g and g["due_date"] == "2026-10-04", "groceries tomorrow 2026-10-04")

chat("move the dentist one to friday")
chat("rename the groceries task to buy vegetables and fruits")
chat("mark it as done")
chat("delete the call mom task")
chat("what is on my list?")
show()
t = tasks()
check(len(t) == 2, "2 tasks left after delete, update did not duplicate")
d = next((x for x in t if "dentist" in x["title"].lower()), None)
check(d and d["due_date"] == "2026-10-09", "dentist moved to Fri 2026-10-09")
v = next((x for x in t if "vegetable" in x["title"].lower()), None)
check(v and v["completed"] and v["due_date"] == "2026-10-04", "groceries renamed, marked done via 'it', date kept")
check(not any("mom" in x["title"].lower() for x in t), "call mom deleted")

chat("add a task submit report in 10 days")
r = next((x for x in tasks() if "report" in x["title"].lower()), None)
check(r and r["due_date"] == "2026-10-13", "in 10 days -> 2026-10-13")

c = sqlite3.connect("todo.db")
uid = c.execute("select id from user where email=?", (email,)).fetchone()[0]
c.execute("delete from task where user_id=?", (uid,)); c.execute("delete from user where id=?", (uid,)); c.commit()
print("\nFAILURES:", failures or "none")
sys.exit(1 if failures else 0)
