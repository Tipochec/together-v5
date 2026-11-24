JS = r"""
let _stickersCache = null;
async function getStickersMap() {
    if (_stickersCache) return _stickersCache;
    try {
        if (window.pywebview && pywebview.api && pywebview.api.get_stickers) {
            _stickersCache = await pywebview.api.get_stickers();
        }
    } catch(e) {
        console.error("getStickersMap error:", e);
        _stickersCache = {};
    }
    return _stickersCache || {};
}

function scrollToBottom(smooth = false) {
    const chat = document.getElementById("chat-list");
    if (!chat) return;
    if (smooth) {
        chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
    } else {
        chat.scrollTop = chat.scrollHeight;
    }
}

function isUserNearBottom() {
    const chat = document.getElementById("chat-list");
    if (!chat) return true;
    const distanceToBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight;
    return distanceToBottom <= 90;
}

async function loadChat() {
    let stickersMap = {};
    try {
        stickersMap = await getStickersMap();
    } catch(e) {
        console.error("getStickersMap failed:", e);
    }

    let messages = [];
    try {
        if (window.pywebview && pywebview.api && pywebview.api.get_chat_history) {
            messages = await pywebview.api.get_chat_history();
        }
    } catch(e) {
        console.error("get_chat_history failed:", e);
    }

    const chat = document.getElementById("chat-list");
    const container = document.getElementById("messages-body") || chat;
    const wasNearBottom = isUserNearBottom();

    container.innerHTML = "";

    if (!messages || messages.length === 0) {
        container.innerHTML = `
            <div class="empty-chat">
                <div class="empty-chat-icon">💌</div>
                <div class="empty-chat-title">Здесь пока тихо</div>
                <div class="empty-chat-desc">Напишите партнёру тёплое сообщение!</div>
            </div>
        `;
        if (wasNearBottom) {
            scrollToBottom();
        }
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

        // Цитата сообщения, на которое ответили
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

        // Стикер (котик)
        if (msg.sticker) {
            div.classList.add("has-sticker");
            if (!msg.text) {
                div.classList.add("sticker-only");
            }
            const stickerBox = document.createElement("div");
            stickerBox.className = "msg-sticker-container";
            const img = document.createElement("img");
            img.className = "msg-sticker-img";
            let src = msg.sticker;
            if (stickersMap && stickersMap[msg.sticker]) {
                src = stickersMap[msg.sticker];
            }
            img.src = src;
            img.alt = "Котик";
            img.title = "Котик 🐾 (нажми на меня!)";
            img.draggable = false;
            img.onclick = (e) => {
                e.stopPropagation();
                img.style.transform = "scale(1.18) rotate(4deg)";
                setTimeout(() => { img.style.transform = ""; }, 220);
            };
            stickerBox.appendChild(img);
            div.appendChild(stickerBox);
        }

        if (msg.text) {
            const body = document.createElement("div");
            body.className = "msg-text";
            body.textContent = msg.text;
            if (isOnlyEmojis(msg.text) && !msg.sticker) {
                body.classList.add("big-emoji");
            }
            div.appendChild(body);
        }

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
            copyMessageText(msg.text || (msg.sticker ? "🐾 Стикер Котик" : ""), copyBtn);
        };
        actions.appendChild(copyBtn);

        div.appendChild(actions);

        container.appendChild(div);
    }

    const bubble = document.getElementById("typing-bubble");
    if (bubble) {
        bubble.style.display = _partnerIsTyping ? "inline-flex" : "none";
    }
    if (wasNearBottom) {
        scrollToBottom();
    }
}

// ── Ответ на конкретное сообщение ─────────────────────────────────────
function startReply(msg) {
    window._replyingTo = {
        msg_uid: msg.msg_uid || null,
        sender: msg.incoming ? (msg.sender || "Партнёр") : "Вы",
        text: msg.text || (msg.sticker ? "🐾 Стикер Котик" : ""),
    };
    document.getElementById("reply-preview-sender").textContent = window._replyingTo.sender;
    document.getElementById("reply-preview-text").textContent = window._replyingTo.text;
    document.getElementById("reply-preview").style.display = "flex";
    requestAnimationFrame(() => {
        scrollToBottom(true);
        setTimeout(() => scrollToBottom(true), 50);
    });
    const input = document.getElementById("message");
    if (input) input.focus();
}

async function sendCatSticker(btnEl) {
    if (btnEl) {
        btnEl.style.transform = "scale(0.88)";
        setTimeout(() => { btnEl.style.transform = ""; }, 180);
    }
    const picker = document.getElementById("emoji-picker");
    if (picker) picker.style.display = "none";

    const input = document.getElementById("message");
    const text = input ? input.value.trim().slice(0, 500) : "";
    const replying = window._replyingTo || null;

    if (input) {
        input.value = "";
        autoResizeMessageBox();
        updateCharCounter();
        input.focus();
    }
    cancelReply();
    if (_typingTimer) clearTimeout(_typingTimer);
    _typingTimer = null;
    if (_lastSentTyping > 0) {
        reportTyping(false);
        _lastSentTyping = 0;
    }

    try {
        if (window.pywebview && pywebview.api && pywebview.api.send_message) {
            await pywebview.api.send_message(
                text,
                replying ? replying.msg_uid : null,
                replying ? replying.sender : null,
                replying ? replying.text : null,
                "cat"
            );
        }
        await loadChat();
    } catch(e) {
        console.error("sendCatSticker error:", e);
    }
}

function cancelReply() {
    window._replyingTo = null;
    document.getElementById("reply-preview").style.display = "none";
    requestAnimationFrame(() => {
        if (isUserNearBottom()) {
            scrollToBottom(false);
        }
    });
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
    if (_typingTimer) clearTimeout(_typingTimer);
    _typingTimer = null;
    if (_lastSentTyping > 0) {
        reportTyping(false);
        _lastSentTyping = 0;
    }
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
    if (!input.value) {
        input.style.height = "38px";
        input.style.overflowY = "hidden";
        input.classList.remove("has-scroll");
        return;
    }
    input.style.height = "auto";
    const scrollH = input.scrollHeight;
    if (scrollH > 110) {
        input.style.height = "110px";
        input.style.overflowY = "auto";
        input.classList.add("has-scroll");
    } else {
        input.style.height = Math.max(38, scrollH) + "px";
        input.style.overflowY = "hidden";
        input.classList.remove("has-scroll");
    }
}

function updateCharCounter() {
    const input = document.getElementById("message");
    const counter = document.getElementById("char-counter");
    if (!input || !counter) return;
    const len = input.value.length;
    if (len >= 350) {
        counter.textContent = `${len}/500`;
        counter.style.display = "block";
        input.style.paddingRight = "48px";
        if (len >= 500) {
            counter.className = "char-counter limit";
        } else if (len >= 450) {
            counter.className = "char-counter warn";
        } else {
            counter.className = "char-counter";
        }
    } else {
        counter.style.display = "none";
        input.style.paddingRight = "12px";
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

const DEFAULT_RECENTS = ["❤️", "✨", "🥰", "😊", "😂", "🥺", "🔥", "😘"];
let _recentItems = [...DEFAULT_RECENTS];
let _recentLoadedFromBackend = false;

async function loadRecentFromBackend() {
    if (_recentLoadedFromBackend) return _recentItems;
    try {
        if (window.pywebview && pywebview.api && pywebview.api.get_recent_emojis) {
            const res = await pywebview.api.get_recent_emojis();
            if (Array.isArray(res) && res.length > 0) {
                _recentItems = res.filter(x => x && x !== "cat").slice(0, 16);
                _recentLoadedFromBackend = true;
            }
        }
    } catch(e) {}
    _recentItems = _recentItems.filter(x => x && x !== "cat");
    return _recentItems;
}

function recordRecentItem(item) {
    if (!item || item === "cat") return;
    try {
        _recentItems = [item, ..._recentItems.filter(x => x !== item && x !== "cat")].slice(0, 16);
        renderRecentEmojis();
        if (window.pywebview && pywebview.api && pywebview.api.save_recent_emojis) {
            pywebview.api.save_recent_emojis(_recentItems).catch(() => {});
        }
    } catch(e) {
        console.error("recordRecentItem error:", e);
    }
}

function renderRecentEmojis() {
    const rGrid = document.getElementById("recent-emoji-grid");
    if (!rGrid) return;
    rGrid.innerHTML = "";
    for (const item of _recentItems) {
        if (!item || item === "cat") continue;
        const el = document.createElement("span");
        el.className = "emoji-item";
        el.textContent = item;
        el.onclick = () => insertEmoji(item);
        rGrid.appendChild(el);
    }
}

async function renderStickersPicker() {
    const sGrid = document.getElementById("stickers-grid");
    if (!sGrid) return;
    sGrid.innerHTML = "";
    const stickersMap = await getStickersMap();
    if (stickersMap && stickersMap["cat"]) {
        const item = document.createElement("div");
        item.className = "sticker-item";
        item.title = "Отправить котика 🐾";
        const img = document.createElement("img");
        img.src = stickersMap["cat"];
        img.alt = "Котик";
        item.appendChild(img);
        item.onclick = (e) => {
            e.stopPropagation();
            sendCatSticker(item);
        };
        sGrid.appendChild(item);
    }
}

async function toggleEmojiPicker() {
    const panel = document.getElementById("emoji-picker");
    if (!panel) return;

    if (panel.style.display === "block") {
        panel.style.display = "none";
        return;
    }

    // Загружаем сохранённые из бэкенда и обновляем стикеры и часто используемые
    await loadRecentFromBackend();
    await renderStickersPicker();
    await renderRecentEmojis();

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
    recordRecentItem(emoji);
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

// ── Логика статуса набора текста ("Печатает...") ───────────────────────
let _typingTimer = null;
let _lastSentTyping = 0;

function reportTyping(isTyping) {
    if (window.pywebview && pywebview.api && pywebview.api.send_typing_status) {
        pywebview.api.send_typing_status(!!isTyping).catch(() => {});
    }
}

function handleUserTyping() {
    const input = document.getElementById("message");
    const val = input ? input.value.trim() : "";
    const now = Date.now();

    if (!val) {
        if (_typingTimer) clearTimeout(_typingTimer);
        _typingTimer = null;
        if (_lastSentTyping > 0) {
            reportTyping(false);
            _lastSentTyping = 0;
        }
        return;
    }

    // Шлём сигнал "печатает" не чаще 1 раза в 2.5 секунды при активном наборе
    if (now - _lastSentTyping > 2500) {
        reportTyping(true);
        _lastSentTyping = now;
    }

    if (_typingTimer) clearTimeout(_typingTimer);
    _typingTimer = setTimeout(() => {
        reportTyping(false);
        _lastSentTyping = 0;
    }, 3500);
}

let _partnerTypingTimer = null;
let _partnerIsTyping = false;

function onPartnerTyping(isTyping) {
    const wasAlreadyTyping = _partnerIsTyping;
    _partnerIsTyping = !!isTyping;
    const bubble = document.getElementById("typing-bubble");

    if (_partnerTypingTimer) {
        clearTimeout(_partnerTypingTimer);
        _partnerTypingTimer = null;
    }

    if (!bubble) return;

    if (isTyping) {
        const nearBottom = isUserNearBottom();
        bubble.style.display = "inline-flex";
        if (nearBottom && !wasAlreadyTyping) {
            scrollToBottom(true);
        }
        // Автоматически скрываем через 5 секунд, если новый сигнал не пришел
        _partnerTypingTimer = setTimeout(() => {
            _partnerIsTyping = false;
            bubble.style.display = "none";
        }, 5000);
    } else {
        bubble.style.display = "none";
    }
}

let _testTypingInterval = null;
function toggleTestTyping() {
    const btn = document.getElementById("btn-test-typing");
    if (_testTypingInterval || _partnerIsTyping) {
        if (_testTypingInterval) clearInterval(_testTypingInterval);
        _testTypingInterval = null;
        onPartnerTyping(false);
        if (btn) {
            btn.style.background = "";
            btn.style.color = "#a29bfe";
        }
    } else {
        onPartnerTyping(true);
        if (btn) {
            btn.style.background = "rgba(108, 92, 231, 0.35)";
            btn.style.color = "#fff";
        }
        _testTypingInterval = setInterval(() => {
            onPartnerTyping(true);
        }, 2500);
    }
}

window.addEventListener("pywebviewready", () => {
    loadChat();
    loadRecentFromBackend();
    const input = document.getElementById("message");
    if (input) {
        autoResizeMessageBox();
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
            handleUserTyping();
        });
        input.addEventListener("blur", () => {
            if (_typingTimer) clearTimeout(_typingTimer);
            _typingTimer = null;
            if (_lastSentTyping > 0) {
                reportTyping(false);
                _lastSentTyping = 0;
            }
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

    document.addEventListener("keydown", (e) => {
        if (e.ctrlKey && e.altKey && (e.key === "t" || e.key === "T" || e.key === "е" || e.key === "Е")) {
            e.preventDefault();
            toggleTestTyping();
        }
    });
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
