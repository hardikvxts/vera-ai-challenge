import time
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from services.llm import generate_message
from services.data_loader import load_all_data
from services.message_builder import build_message
from store import contexts, versions, conversations

app = FastAPI(title="Magicpin Vera AI Challenge Bot")
seed_data = load_all_data()
START_TIME = time.time()


@app.get("/")
def home():
    return {
        "service": "Magicpin Vera AI Challenge Bot",
        "status": "running",
        "team": "Hardik Vats",
        "version": "1.0",
        "demo_ui": "/demo",
        "docs": "/docs",
        "health": "/v1/healthz",
        "metadata": "/v1/metadata"
    }


@app.get("/v1/healthz")
def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": {
            "category": len(contexts["category"]),
            "merchant": len(contexts["merchant"]),
            "customer": len(contexts["customer"]),
            "trigger": len(contexts["trigger"])
        }
    }


@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Hardik Vats",
        "team_members": ["Hardik Vats"],
        "model": "Groq Llama 3.3 70B + Rule Engine",
        "approach": "Contextual message generation with deterministic fallback",
        "contact_email": "hardiksharmavats@gmail.com",
        "version": "1.0",
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }


@app.post("/v1/context")
def context(payload: dict):
    scope = payload.get("scope")
    context_id = payload.get("context_id")
    version = payload.get("version", 1)

    if scope not in contexts:
        return {"accepted": False, "reason": "invalid_scope"}

    current_version = versions.get(context_id, 0)
    if version <= current_version:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": current_version
        }

    contexts[scope][context_id] = payload.get("payload", {})
    versions[context_id] = version

    return {
        "accepted": True,
        "ack_id": f"ack_{context_id}_v{version}",
        "stored_at": datetime.now(timezone.utc).isoformat()
    }


@app.post("/v1/tick")
def tick(payload: dict):
    actions = []
    trigger_ids = payload.get("available_triggers", [])

    for trigger_id in trigger_ids:
        trigger = contexts["trigger"].get(trigger_id)
        if not trigger:
            continue

        merchant_id = trigger.get("merchant_id")
        merchant = contexts["merchant"].get(merchant_id)
        if not merchant:
            continue

        message = build_message(merchant, trigger)
        actions.append({
            "conversation_id": f"conv_{trigger_id}",
            "merchant_id": merchant_id,
            "customer_id": trigger.get("customer_id"),
            "send_as": "vera",
            "trigger_id": trigger_id,
            "template_name": "vera_ai",
            "template_params": [],
            "body": message,
            "cta": "open_ended",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": "Generated using category, merchant, trigger and customer context"
        })

    return {"actions": actions}


@app.post("/v1/reply")
def reply(payload: dict):
    message = payload.get("message", "").lower().strip()

    auto_reply_phrases = [
        "thank you for contacting", "we will respond shortly",
        "business account", "our team will respond",
        "this is an automated", "auto-reply", "out of office"
    ]
    if any(phrase in message for phrase in auto_reply_phrases):
        return {
            "action": "end",
            "rationale": "Detected auto-reply pattern"
        }

    hostile_phrases = [
        "stop", "spam", "useless", "not interested", "unsubscribe",
        "don't message", "dont message", "leave me alone", "block"
    ]
    if any(phrase in message for phrase in hostile_phrases):
        return {
            "action": "end",
            "rationale": "Merchant opted out"
        }

    positive_phrases = [
        "yes", "ok", "sure", "send", "do it", "lets do it",
        "let's do it", "go ahead", "proceed", "please", "haan",
        "okay", "sounds good", "interested", "tell me more",
        "what's next", "whats next"
    ]

    try:
        reply_prompt = (
            f"Merchant replied: {message}\n"
            "Decide the next action: send, wait, or end.\n"
            "Rules:\n"
            "- If merchant shows positive intent or agreement, return send\n"
            "- If merchant declined or wants to stop, return end\n"
            "- If merchant is unclear or needs time, return wait\n"
            "Return only one word."
        )

        decision = generate_message(reply_prompt).strip().lower()

        if "send" in decision:
            return {
                "action": "send",
                "body": "Done. Preparing your personalized recommendation based on your latest performance data and customer trends. You'll see the drafts shortly.",
                "cta": "open_ended",
                "rationale": "Detected positive intent"
            }
        if "end" in decision:
            return {
                "action": "end",
                "rationale": "Detected decline intent"
            }
        if "wait" in decision:
            return {
                "action": "wait",
                "wait_seconds": 1800,
                "rationale": "Requires clarification"
            }
    except Exception:
        pass

    if any(phrase in message for phrase in positive_phrases):
        return {
            "action": "send",
            "body": "Done. Preparing your personalized recommendation based on your latest performance data and customer trends. You'll see the drafts shortly.",
            "cta": "open_ended",
            "rationale": "Keyword match: positive intent"
        }

    return {
        "action": "wait",
        "wait_seconds": 1800,
        "rationale": "Awaiting clearer merchant intent"
    }


@app.post("/v1/teardown")
def teardown():
    for ctx in contexts.values():
        ctx.clear()
    versions.clear()
    conversations.clear()
    return {"success": True}


@app.get("/v1/debug")
def debug():
    return {
        "merchant_keys": list(seed_data["merchants"].keys()),
        "customer_keys": list(seed_data["customers"].keys()),
        "trigger_keys": list(seed_data["triggers"].keys())
    }


@app.get("/v1/sample")
def sample():
    return seed_data["merchants"]


@app.get("/v1/check")
def check():
    return contexts["merchant"]


@app.get("/v1/merchant/{idx}")
def merchant(idx: int):
    return seed_data["merchants"]["merchants"][idx]


@app.get("/v1/simulate/{idx}")
def simulate(idx: int):
    m = seed_data["merchants"]["merchants"][idx]
    message = build_message(m, {})
    return {
        "merchant": m["identity"]["name"],
        "message": message
    }


@app.get("/v1/all_merchants")
def all_merchants():
    return {
        "count": len(seed_data["merchants"]["merchants"]),
        "ids": [m["merchant_id"] for m in seed_data["merchants"]["merchants"]]
    }


@app.get("/demo", response_class=HTMLResponse)
def demo():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vera AI - Live Chat Demo</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
    .chat-container { width: 100%; max-width: 600px; background: #1e293b; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); overflow: hidden; display: flex; flex-direction: column; height: 85vh; border: 1px solid #334155; }
    .chat-header { background: #0f172a; padding: 16px 20px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
    .chat-header h1 { font-size: 1.1rem; font-weight: 600; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
    .chat-header .badge { background: #0284c7; color: #fff; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; }
    .selector { padding: 12px 20px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 10px; font-size: 0.9rem; }
    .selector select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; padding: 6px 12px; border-radius: 8px; outline: none; font-size: 0.85rem; flex: 1; }
    .chat-body { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
    .msg { max-width: 82%; padding: 12px 16px; border-radius: 14px; font-size: 0.92rem; line-height: 1.45; white-space: pre-wrap; word-wrap: break-word; }
    .msg.bot { background: #334155; color: #f1f5f9; align-self: flex-start; border-bottom-left-radius: 4px; }
    .msg.bot .sender { font-size: 0.75rem; font-weight: 600; color: #38bdf8; margin-bottom: 4px; }
    .msg.user { background: #2563eb; color: #ffffff; align-self: flex-end; border-bottom-right-radius: 4px; }
    .msg.user .sender { font-size: 0.75rem; font-weight: 600; color: #93c5fd; margin-bottom: 4px; text-align: right; }
    .decision-badge { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; margin-bottom: 6px; display: inline-block; }
    .action-send { background: #16a34a; color: #fff; }
    .action-wait { background: #d97706; color: #fff; }
    .action-end { background: #dc2626; color: #fff; }
    .chat-footer { padding: 14px 20px; background: #0f172a; border-top: 1px solid #334155; display: flex; gap: 10px; }
    .chat-footer input { flex: 1; background: #1e293b; color: #fff; border: 1px solid #475569; padding: 10px 14px; border-radius: 10px; outline: none; font-size: 0.9rem; }
    .chat-footer input:focus { border-color: #38bdf8; }
    .chat-footer button { background: #0284c7; color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: 0.2s; }
    .chat-footer button:hover { background: #0369a1; }
    .quick-replies { display: flex; gap: 6px; padding: 0 20px 10px; background: #0f172a; flex-wrap: wrap; }
    .quick-btn { background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; cursor: pointer; }
    .quick-btn:hover { background: #334155; color: #fff; }
  </style>
</head>
<body>
  <div class="chat-container">
    <div class="chat-header">
      <h1><span>🤖</span> Vera AI Assistant</h1>
      <span class="badge">Hardik Vats</span>
    </div>
    <div class="selector">
      <label for="merchant-select">Simulate as:</label>
      <select id="merchant-select" onchange="loadSimulation()">
        <option value="0">Dr. Meera's Dental Clinic (Merchant #0)</option>
        <option value="1">FitZone Gym (Merchant #1)</option>
        <option value="2">Apex Diagnostics (Merchant #2)</option>
        <option value="3">Glow Salon & Spa (Merchant #3)</option>
      </select>
    </div>
    <div class="chat-body" id="chat-body">
      <!-- Messages injected here -->
    </div>
    <div class="quick-replies">
      <span style="font-size:0.75rem; color:#64748b; align-self:center;">Try:</span>
      <button class="quick-btn" onclick="sendQuick('Yes, please generate the campaign drafts!')">"Yes, send drafts"</button>
      <button class="quick-btn" onclick="sendQuick('No, stop sending these messages.')">"No, stop"</button>
      <button class="quick-btn" onclick="sendQuick('Can we discuss this next week instead?')">"Next week"</button>
    </div>
    <form class="chat-footer" onsubmit="handleSend(event)">
      <input type="text" id="user-input" placeholder="Type your reply as the merchant..." autocomplete="off" />
      <button type="submit">Reply</button>
    </form>
  </div>

  <script>
    const chatBody = document.getElementById('chat-body');
    const userInput = document.getElementById('user-input');

    async function loadSimulation() {
      const idx = document.getElementById('merchant-select').value;
      chatBody.innerHTML = '<div style="text-align:center;color:#64748b;font-size:0.85rem;margin:auto;">Loading merchant simulation...</div>';
      try {
        const res = await fetch(`/v1/simulate/${idx}`);
        const data = await res.json();
        chatBody.innerHTML = `
          <div class="msg bot">
            <div class="sender">Vera AI ➔ ${data.merchant}</div>
            <div>${data.message}</div>
          </div>
        `;
      } catch (err) {
        chatBody.innerHTML = `<div style="color:#ef4444;text-align:center;">Error loading simulation</div>`;
      }
    }

    async function handleSend(e) {
      if (e) e.preventDefault();
      const text = userInput.value.trim();
      if (!text) return;

      userInput.value = '';

      const userDiv = document.createElement('div');
      userDiv.className = 'msg user';
      userDiv.innerHTML = `<div class="sender">You (Merchant)</div><div>${text}</div>`;
      chatBody.appendChild(userDiv);
      chatBody.scrollTop = chatBody.scrollHeight;

      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'msg bot';
      loadingDiv.id = 'loading-msg';
      loadingDiv.innerHTML = `<div style="color:#94a3b8;font-style:italic;">Vera is thinking...</div>`;
      chatBody.appendChild(loadingDiv);
      chatBody.scrollTop = chatBody.scrollHeight;

      try {
        const res = await fetch('/v1/reply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        
        loadingDiv.remove();
        const botDiv = document.createElement('div');
        botDiv.className = 'msg bot';
        
        let actionClass = 'action-send';
        if (data.action === 'wait') actionClass = 'action-wait';
        if (data.action === 'end') actionClass = 'action-end';

        let content = `<span class="decision-badge ${actionClass}">Decision: ${data.action}</span>`;
        if (data.body) {
          content += `<div>${data.body}</div>`;
        } else if (data.action === 'wait') {
          content += `<div>Understood. Pausing notifications for 30 minutes.</div>`;
        } else if (data.action === 'end') {
          content += `<div>Opted out. Conversation closed gracefully.</div>`;
        }
        if (data.rationale) {
          content += `<div style="font-size:0.75rem;color:#94a3b8;margin-top:6px;">ℹ️ ${data.rationale}</div>`;
        }

        botDiv.innerHTML = `<div class="sender">Vera AI</div>${content}`;
        chatBody.appendChild(botDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
      } catch (err) {
        loadingDiv.innerHTML = `<div style="color:#ef4444;">Error processing reply.</div>`;
      }
    }

    function sendQuick(txt) {
      userInput.value = txt;
      handleSend();
    }

    loadSimulation();
  </script>
</body>
</html>
"""
