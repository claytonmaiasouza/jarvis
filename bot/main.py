import os
import json
import logging
import base64
import subprocess
from pathlib import Path
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

ALLOWED_USER_ID = int(os.environ["TELEGRAM_USER_ID"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = Anthropic(api_key=ANTHROPIC_API_KEY)
sessions: dict[int, list] = {}

PROJECT_PATHS = {
    "agendamento":         "/opt/agendamento",
    "bot-restaurante":     "/opt/bot-restaurante",
    "farmacia-santaclara": "/opt/farmacia-santaclara",
    "fintrack":            "/opt/fintrack",
    "jarvis":              "/opt/jarvis",
}


def load_project_contexts() -> str:
    sections = []
    for name, path in PROJECT_PATHS.items():
        claude_md = os.path.join(path, "CLAUDE.md")
        if os.path.exists(claude_md):
            with open(claude_md) as f:
                sections.append(f"## {name}\n{f.read().strip()}")
        else:
            sections.append(f"## {name}\n(no CLAUDE.md)")
    return "\n\n".join(sections)


SYSTEM_PROMPT = f"""You are Jarvis, an autonomous senior engineer agent managing a VPS with multiple SaaS projects.
Be extremely concise. No fluff. Caveman mode. Act like a senior engineer.
Use tools to actually do things — don't describe, just do.
For destructive operations (delete files, drop tables, rm -rf), ask user first.

# Projects
{load_project_contexts()}
"""

TOOLS = [
    {
        "name": "bash",
        "description": "Run any bash command on the VPS. Use for anything: git, docker, file ops, db queries, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string", "description": "Working directory (optional)"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file from the VPS",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file on the VPS",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "deploy",
        "description": "git pull + docker compose up --build for a project",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "enum": list(PROJECT_PATHS.keys())}
            },
            "required": ["project"]
        }
    },
    {
        "name": "docker_logs",
        "description": "Get recent logs from a docker container",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "lines": {"type": "integer"}
            },
            "required": ["container"]
        }
    }
]


def run_bash(command: str, cwd: str = None) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        return (r.stdout + r.stderr).strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, inputs: dict) -> str:
    if name == "bash":
        return run_bash(inputs["command"], inputs.get("cwd"))

    elif name == "read_file":
        try:
            return Path(inputs["path"]).read_text()
        except Exception as e:
            return f"Error: {e}"

    elif name == "write_file":
        try:
            p = Path(inputs["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(inputs["content"])
            return f"Written: {inputs['path']}"
        except Exception as e:
            return f"Error: {e}"

    elif name == "deploy":
        project = inputs["project"]
        path = PROJECT_PATHS[project]
        return run_bash("git pull && docker compose up -d --build", cwd=path)

    elif name == "docker_logs":
        lines = inputs.get("lines", 100)
        return run_bash(f"docker logs --tail {lines} {inputs['container']} 2>&1")

    return f"Unknown tool: {name}"


def is_allowed(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


async def run_agent(history: list, update: Update) -> str:
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        text_parts = [b.text for b in response.content if b.type == "text"]
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            final = "\n".join(text_parts)
            history.append({"role": "assistant", "content": final or "(done)"})
            return final

        if text_parts:
            await update.message.reply_text("\n".join(text_parts))

        history.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool in tool_uses:
            await update.message.reply_text(f"⚙️ `{tool.name}`: `{str(tool.input)[:200]}`", parse_mode="Markdown")
            result = execute_tool(tool.name, tool.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": result[:8000],
            })

        history.append({"role": "user", "content": tool_results})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    sessions[update.effective_user.id] = []
    await update.message.reply_text(
        "Jarvis online.\n\n"
        "Pode mandar texto ou foto.\n"
        "/status — containers\n"
        "/clear — limpa contexto"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    sessions[update.effective_user.id] = []
    await update.message.reply_text("Context cleared.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    out = run_bash("docker ps --format 'table {{.Names}}\t{{.Status}}'")
    await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return

    history = sessions.setdefault(user_id, [])

    if len(history) > 28:
        sessions[user_id] = history[-28:]
        history = sessions[user_id]

    content = []

    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        data = await file.download_as_bytearray()
        b64 = base64.standard_b64encode(data).decode()
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
        text = update.message.caption or "Analisa essa imagem."
        content.append({"type": "text", "text": text})
    else:
        content.append({"type": "text", "text": update.message.text})

    history.append({"role": "user", "content": content})

    await update.message.reply_text("⏳")

    reply = await run_agent(history, update)

    if reply:
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND) | filters.PHOTO,
        handle_message
    ))
    app.run_polling()


if __name__ == "__main__":
    main()
