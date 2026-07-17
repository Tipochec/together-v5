JS = r"""
async function loadChat() {

    const messages = await pywebview.api.get_chat_history();

    const chat = document.getElementById("chat-list");

    chat.innerHTML = "";

    for (const msg of messages) {

        const div = document.createElement("div");

        div.className = msg.incoming
            ? "message partner"
            : "message me";

        const time = new Date(msg.time);

        div.innerHTML = `
            ${msg.incoming ? `<div class="sender">${msg.sender || "Партнёр"}</div>` : ""}
            <div>${msg.text}</div>
            <div class="time">
                ${time.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit"
                })}
            </div>
        `;

        chat.appendChild(div);
    }

    chat.scrollTop = chat.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("message");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.disabled = true;
    try {
        await pywebview.api.send_message(text);
        await loadChat();
    } catch (e) {
        console.error("send_message failed:", e);
    } finally {
        input.disabled = false;
        input.focus();
    }
}

// Популярные эмодзи — просто статичный набор, ничего скачивать/грузить
// не нужно, они уже "встроены" как обычный текст (юникод).
const POPULAR_EMOJIS = [
    "😀","😂","🤣","😊","😍","🥰","😘","😉","😎","🤩",
    "🥳","😇","🙃","😅","🤔","🙄","😏","😴","😭","😢",
    "😡","🤯","😱","🥺","😤","🤗","🤤","🙈","💀","👀",
    "❤️","🧡","💛","💚","💙","💜","🖤","💔","💕","💖",
    "👍","👎","👏","🙏","✌️","🤝","💪","👊","🤙","👌",
    "🔥","✨","🎉","🎁","⭐","💯","☕","🍕","🍺","🌹",
];

let _emojiPickerFilled = false;

function toggleEmojiPicker() {
    const panel = document.getElementById("emoji-picker");
    if (!panel) return;

    if (panel.style.display === "block") {
        panel.style.display = "none";
        return;
    }

    if (!_emojiPickerFilled) {
        const grid = document.getElementById("emoji-grid");
        grid.innerHTML = POPULAR_EMOJIS
            .map(e => `<span class="emoji-item" onclick="insertEmoji('${e}')">${e}</span>`)
            .join("");
        _emojiPickerFilled = true;
    }
    panel.style.display = "block";
}

function insertEmoji(emoji) {
    const input = document.getElementById("message");
    if (input) {
        const start = input.selectionStart ?? input.value.length;
        const end   = input.selectionEnd   ?? input.value.length;
        input.value = input.value.slice(0, start) + emoji + input.value.slice(end);
        const caret = start + emoji.length;
        input.focus();
        input.setSelectionRange(caret, caret);
    }
    document.getElementById("emoji-picker").style.display = "none";
}

// Клик мимо панели — закрываем её
document.addEventListener("click", (ev) => {
    const panel = document.getElementById("emoji-picker");
    const btn   = document.getElementById("emoji-toggle-btn");
    if (!panel || panel.style.display !== "block") return;
    if (!panel.contains(ev.target) && ev.target !== btn) {
        panel.style.display = "none";
    }
});

async function clearChat() {
    document.getElementById("confirm-overlay").style.display = "flex";
}

function hideConfirm() {
    document.getElementById("confirm-overlay").style.display = "none";
}

async function confirmClearChat() {
    hideConfirm();
    try {
        await pywebview.api.clear_chat();
        await loadChat();
    } catch (e) {
        console.error("clear_chat failed:", e);
    }
}

window.addEventListener("pywebviewready", () => {
    loadChat();
    const input = document.getElementById("message");
    if (input) {
        input.focus();
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                sendMessage();
            }
        });
    }
});
"""