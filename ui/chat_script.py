JS = r"""
async function loadChat() {

    const messages = await pywebview.api.get_chat_history();

    const chat = document.getElementById("chat-list");

    chat.innerHTML = "";

    if (!messages || messages.length === 0) {
        chat.innerHTML = `
            <div class="empty-chat">
                <div class="empty-chat-icon">💌</div>
                <div class="empty-chat-title">Здесь пока тихо</div>
                <div class="empty-chat-desc">Напишите партнёру тёплое сообщение!</div>
            </div>
        `;
        return;
    }

    for (const msg of messages) {

        const div = document.createElement("div");

        div.className = msg.incoming
            ? "message partner"
            : "message me";

        if (msg.incoming) {
            const sender = document.createElement("div");
            sender.className = "sender";
            sender.textContent = msg.sender || "Партнёр";
            div.appendChild(sender);
        }

        // Цитата сообщения, на которое ответили — текст цитаты хранится
        // прямо в этом сообщении (reply_text/reply_sender), а не
        // подгружается по ссылке на оригинал, поэтому показывается даже
        // если у партнёра то исходное сообщение уже удалено/недоступно.
        if (msg.reply_text) {
            const quote = document.createElement("div");
            quote.className = "reply-quote";
            const quoteSender = document.createElement("div");
            quoteSender.className = "reply-quote-sender";
            quoteSender.textContent = msg.reply_sender || "Сообщение";
            const quoteText = document.createElement("div");
            quoteText.className = "reply-quote-text";
            quoteText.textContent = msg.reply_text;
            quote.appendChild(quoteSender);
            quote.appendChild(quoteText);
            div.appendChild(quote);
        }

        const body = document.createElement("div");
        body.className = "msg-text";
        body.textContent = msg.text;
        if (isOnlyEmojis(msg.text)) {
            body.classList.add("big-emoji");
        }
        div.appendChild(body);

        const footer = document.createElement("div");
        footer.className = "msg-footer";
        const time = new Date(msg.time);
        const timeEl = document.createElement("span");
        timeEl.className = "time";
        timeEl.textContent = time.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        });
        footer.appendChild(timeEl);
        div.appendChild(footer);

        const actions = document.createElement("div");
        actions.className = "msg-actions";

        const replyBtn = document.createElement("button");
        replyBtn.className = "action-pill-btn";
        replyBtn.title = "Ответить";
        replyBtn.textContent = "↩";
        replyBtn.onclick = (e) => {
            e.stopPropagation();
            startReply(msg);
        };
        actions.appendChild(replyBtn);

        const copyBtn = document.createElement("button");
        copyBtn.className = "action-pill-btn";
        copyBtn.title = "Скопировать сообщение";
        copyBtn.textContent = "📋";
        copyBtn.onclick = (e) => {
            e.stopPropagation();
            copyMessageText(msg.text, copyBtn);
        };
        actions.appendChild(copyBtn);

        div.appendChild(actions);

        chat.appendChild(div);
    }

    chat.scrollTop = chat.scrollHeight;
}

// ── Ответ на конкретное сообщение ─────────────────────────────────────
function startReply(msg) {
    window._replyingTo = {
        msg_uid: msg.msg_uid || null,
        sender: msg.incoming ? (msg.sender || "Партнёр") : "Вы",
        text: msg.text,
    };
    document.getElementById("reply-preview-sender").textContent = window._replyingTo.sender;
    document.getElementById("reply-preview-text").textContent = window._replyingTo.text;
    document.getElementById("reply-preview").style.display = "flex";
    const input = document.getElementById("message");
    if (input) input.focus();
}

function cancelReply() {
    window._replyingTo = null;
    document.getElementById("reply-preview").style.display = "none";
}

// Копирование текста сообщения в буфер обмена — по клику на 📋,
// которая появляется при наведении на сообщение (см. .msg-copy в CSS).
function copyMessageText(text, btn) {
    const showCopied = () => {
        if (!btn) return;
        const original = btn.textContent;
        btn.textContent = "✓";
        setTimeout(() => { btn.textContent = original; }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(showCopied).catch(() => _fallbackCopy(text, showCopied));
    } else {
        _fallbackCopy(text, showCopied);
    }
}

function _fallbackCopy(text, cb) {
    try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        if (cb) cb();
    } catch (e) {
        console.error("copy failed:", e);
    }
}

async function sendMessage() {
    const input = document.getElementById("message");
    const text = input.value.trim().slice(0, 500);
    if (!text) return;

    const replying = window._replyingTo || null;

    input.value = "";
    autoResizeMessageBox();
    updateCharCounter();
    cancelReply();
    input.disabled = true;
    try {
        await pywebview.api.send_message(
            text,
            replying ? replying.msg_uid : null,
            replying ? replying.sender : null,
            replying ? replying.text : null
        );
        await loadChat();
    } catch (e) {
        console.error("send_message failed:", e);
    } finally {
        input.disabled = false;
        input.focus();
    }
}

// Textarea растёт вместе с текстом (до max-height из CSS, дальше — свой
// скролл внутри поля), а не остаётся однострочным — иначе перенос строки
// по Shift+Enter был бы не виден, пока не проскроллишь само поле.
function autoResizeMessageBox() {
    const input = document.getElementById("message");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = input.scrollHeight + "px";
}

function updateCharCounter() {
    const input = document.getElementById("message");
    const counter = document.getElementById("char-counter");
    if (!input || !counter) return;
    const len = input.value.length;
    if (len >= 350) {
        counter.textContent = `${len}/500`;
        counter.style.display = "block";
        if (len >= 500) {
            counter.className = "char-counter limit";
        } else if (len >= 450) {
            counter.className = "char-counter warn";
        } else {
            counter.className = "char-counter";
        }
    } else {
        counter.style.display = "none";
    }
}

function isOnlyEmojis(str) {
    if (!str) return false;
    const clean = str.trim();
    if (!clean) return false;
    const emojiRegex = /^(?:\p{Extended_Pictographic}|\u200d|\ufe0f|\u20e3|\s)+$/u;
    if (!emojiRegex.test(clean)) return false;
    const count = [...clean.replace(/\s+/g, '')].length;
    return count > 0 && count <= 8;
}

// Все популярные эмодзи подряд без категорий
const ALL_EMOJIS = [
    // Смайлы и лица
    "😀","😃","😄","😁","😆","😅","🤣","😂","🙂","🙃",
    "😉","😊","😇","🥰","😍","🤩","😘","😗","😚","😙",
    "😋","😛","😜","🤪","😝","🤑","🤗","🤭","🤫","🤔",
    "🤐","🤨","😐","😑","😶","😏","😒","🙄","😬","🤥",
    "😌","😔","😪","🤤","😴","😷","🤒","🤕","🤢","🤮",
    "🤧","🥵","🥶","🥴","😵","🤯","🤠","🥳","🥸","😎",
    "🤓","🧐","😕","😟","🙁","😮","😯","😲","😳","🥺",
    "😦","😧","😰","😥","😢","😭","😱","😖","😣","😞",
    "😓","😩","😫","🥱","😤","😡","😠","🤬","😈","👿",
    "💀","☠️","💩","🤡","👻","👽","🤖","👾","🙈","👀",
    // Сердца
    "❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔",
    "❣️","💕","💞","💓","💗","💖","💘","💝","💟","💌",
    "💋","🫂","💍","💎","💐","🌸","💮","🏵️","🌹","🥀",
    "🌺","🌻","🌼","🌷","🪷","✨","🎀","🧸","🕊️","🕯️",
    // Животные
    "🐱","😸","😹","😻","😼","😽","🙀","😿","😾","🐈",
    "🐶","🐕","🦮","🐩","🐺","🦊","🦝","🦁","🐯","🐅",
    "🐆","🐴","🐎","🦄","🦓","🦌","🐮","🐂","🐷","🐖",
    "🐽","🐏","🐑","🐐","🐪","🐫","🦒","🐘","🐭","🐁",
    "🐹","🐰","🐇","🐿️","🦔","🦇","🐻","🐨","🐼","🦥",
    "🐾","🐦","🐧","🦆","🦉","🐸","🐢","🦎","🐙","🐬",
    // Еда
    "☕","🍵","🧃","🥤","🧋","🍶","🍺","🍻","🥂","🍷",
    "🥃","🍸","🍹","🍾","🍕","🍔","🍟","🌭","🍿","🥓",
    "🍳","🧇","🥞","🍞","🥐","🥖","🥨","🧀","🥗","🥪",
    "🌮","🌯","🍜","🍝","🍣","🍱","🥟","🍤","🍙","🍚",
    "🍦","🍨","🍩","🍪","🎂","🍰","🧁","🍫","🍬","🍭",
    "🍎","🍓","🍒","🍑","🍇","🍉","🍌","🍋","🍊","🥑",
    // Жесты и разное
    "👍","👎","👊","✊","🤛","🤜","👏","🙌","👐","🤲",
    "🤝","🙏","✍️","💅","🤳","💪","✌️","🤞","🤟","🤘",
    "🤙","👈","👉","👆","👇","☝️","👋","🤚","🖐️","✋",
    "🖖","💫","⭐","🌟","⚡","💥","🔥","💯","💢","💨",
    "💦","💤","🎵","🎶","🎮","🎯","🎲","🎁","🎈","🎉"
];

// Каомодзи (текстовые смайлы)
const ALL_KAOMOJIS = [
    "(◕‿◕)", "(｡♥‿♥｡)", "(づ｡◕‿‿◕｡)づ", "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
    "(◡‿◡✿)", "(⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)", "(◕‿◕)♡", "(*^▽^*)",
    "(≧◡≦)", "(o˘◡˘o)", "(っ˘з(˘⌣˘ )", "(♡-_-♡)",
    "(੭ु´･ω･`)੭ु⁾⁾", "(๑•̀ㅂ•́)و✧", "(=^･ω･^=)", "(ฅ^•ﻌ•^ฅ)",
    "(ง'̀-'́)ง", "(╯°□°)╯︵ ┻━┻", "┬─┬ノ( º _ ºノ)", "¯\\_(ツ)_/¯",
    "(｡•́︿•̀｡)", "(╥﹏╥)", "( ˘ ³˘)♥", "(o´∀`o)",
    "(★ω★)", "＼(＾▽＾)／", "(¬‿¬)", "(¬_¬)",
    "(~˘▾˘)~", "(ಥ﹏ಥ)", "٩(◕‿◕｡)۶", "╰(▔∀▔)╯"
];

let _emojiPickerFilled = false;

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function toggleEmojiPicker() {
    const panel = document.getElementById("emoji-picker");
    if (!panel) return;

    if (panel.style.display === "block") {
        panel.style.display = "none";
        return;
    }

    if (!_emojiPickerFilled) {
        const grid = document.getElementById("emoji-grid");
        if (grid) {
            grid.innerHTML = "";
            for (const emoji of ALL_EMOJIS) {
                const el = document.createElement("span");
                el.className = "emoji-item";
                el.textContent = emoji;
                el.onclick = () => insertEmoji(emoji);
                grid.appendChild(el);
            }
        }
        const kGrid = document.getElementById("kaomoji-grid");
        if (kGrid) {
            kGrid.innerHTML = "";
            for (const km of ALL_KAOMOJIS) {
                const el = document.createElement("span");
                el.className = "kaomoji-item";
                el.textContent = km;
                el.onclick = () => insertEmoji(km);
                kGrid.appendChild(el);
            }
        }
        _emojiPickerFilled = true;
    }
    panel.style.display = "block";
}

function insertEmoji(emoji) {
    const input = document.getElementById("message");
    if (input) {
        const start = input.selectionStart ?? input.value.length;
        const end   = input.selectionEnd   ?? input.value.length;
        const current = input.value;
        const before = current.slice(0, start);
        const after = current.slice(end);
        const allowed = 500 - (before.length + after.length);
        if (allowed > 0) {
            const inserted = emoji.slice(0, allowed);
            input.value = before + inserted + after;
            const caret = start + inserted.length;
            input.focus();
            input.setSelectionRange(caret, caret);
            autoResizeMessageBox();
            updateCharCounter();
        }
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
    try {
        pywebview.api.get_state().then(state => {
            if (state && state.partner && state.partner.name) {
                const el = document.getElementById("chat-partner-status");
                if (el) el.textContent = `${state.connected ? "в сети" : "не в сети"} • ${state.partner.name}`;
            }
        }).catch(() => {});
    } catch(e) {}
    const input = document.getElementById("message");
    if (input) {
        input.focus();
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
            // Shift+Enter — перенос строки в textarea
        });
        input.addEventListener("input", () => {
            autoResizeMessageBox();
            updateCharCounter();
        });

        // Предотвращение зависания на Windows 11 при вставке картинок/гифок из буфера
        input.addEventListener("paste", (e) => {
            const cd = e.clipboardData;
            if (!cd) return;
            const text = cd.getData("text/plain");
            if (!text) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }
});

function onHeartReceived(senderName){
  showHeartBanner('ОХАЁ)');
  spawnHeartAnimation();
}

function showHeartBanner(text){
  const old = document.querySelector('.heart-banner');
  if(old) old.remove();
  const banner = document.createElement('div');
  banner.className = 'heart-banner';
  banner.innerHTML = `<span>❤️</span> <span>${escapeHtml(text)}</span>`;
  document.body.appendChild(banner);
  setTimeout(()=>{ if(banner.parentNode) banner.remove(); }, 3200);
}

function spawnHeartAnimation(){
  const container = document.getElementById('heart-burst');
  if(!container) return;
  const hearts = ['❤️', '💖', '💕', '✨', '💓', '💗'];
  for(let i = 0; i < 7; i++){
    setTimeout(()=>{
      const el = document.createElement('div');
      el.className = 'flying-heart';
      el.textContent = hearts[Math.floor(Math.random() * hearts.length)];
      el.style.left = (15 + Math.random() * 70) + '%';
      el.style.top = (40 + Math.random() * 40) + '%';
      container.appendChild(el);
      setTimeout(()=>el.remove(), 1200);
    }, i * 110);
  }
}
"""
