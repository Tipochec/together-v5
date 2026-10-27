CSS = r"""
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
    scrollbar-width:thin;
    scrollbar-color:rgba(255,255,255,0.18) transparent;
}
::-webkit-scrollbar{
    width:5px;
    height:5px;
}
::-webkit-scrollbar-button{
    display:none !important;
    width:0 !important;
    height:0 !important;
}
::-webkit-scrollbar-track{
    background:transparent;
}
::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.18);
    border-radius:10px;
}
::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.3);
}
::-webkit-scrollbar-corner{
    background:transparent;
}

body{
    background:#0f0f13;
    color:#fff;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    height:100vh;
    overflow:hidden;
    -webkit-app-region:no-drag;
    display:flex;
    flex-direction:column;
    user-select:none;
}

/* ── Заголовок (Titlebar) ────────────────────────────────────────────── */
.titlebar{
    height:46px;
    flex-shrink:0;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 14px;
    background:rgba(26,24,32,0.75);
    backdrop-filter:blur(12px);
    border-bottom:1px solid rgba(255,255,255,0.07);
    -webkit-app-region:drag;
}

.title-left{
    display:flex;
    align-items:center;
    gap:8px;
    -webkit-app-region:drag;
}

.title-icon-badge{
    width:28px;
    height:28px;
    border-radius:8px;
    background:linear-gradient(135deg, rgba(108,92,231,0.25), rgba(212,83,126,0.25));
    border:1px solid rgba(255,255,255,0.08);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:14px;
    flex-shrink:0;
}

.title-text-group{
    display:flex;
    flex-direction:column;
}

.title-name{
    font-size:13px;
    font-weight:600;
    color:#fff;
    line-height:1.2;
}

.title-status{
    font-size:10px;
    color:#6ee7b7;
    display:flex;
    align-items:center;
    gap:4px;
}

.title-status-dot{
    width:5px;
    height:5px;
    border-radius:50%;
    background:#10b981;
    box-shadow:0 0 6px #10b981;
}

.title-actions{
    display:flex;
    align-items:center;
    gap:6px;
    -webkit-app-region:no-drag;
}

.title-btn, .close{
    width:28px;
    height:28px;
    border:none;
    border-radius:8px;
    background:rgba(255,255,255,0.05);
    color:rgba(255,255,255,0.6);
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:12px;
    transition:all 0.15s ease;
    -webkit-app-region:no-drag;
}

.title-btn:hover, .close:hover{
    background:rgba(255,255,255,0.12);
    color:#fff;
    transform:translateY(-1px);
}

.title-btn.btn-close:hover{
    background:rgba(239,68,68,0.25);
    color:#ef4444;
}

/* ── Область сообщений ────────────────────────────────────────────────── */
.messages{
    flex:1;
    min-height:0;
    overflow-y:auto;
    padding:16px 14px;
    display:flex;
    flex-direction:column;
    gap:10px;
}

/* Пустое состояние чата */
.empty-chat{
    margin:auto;
    text-align:center;
    padding:20px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
}
.empty-chat-icon{
    font-size:36px;
    margin-bottom:8px;
    animation:pulseHeart 2.4s ease-in-out infinite;
}
@keyframes pulseHeart{
    0%,100%{transform:scale(1);}
    50%{transform:scale(1.12);}
}
.empty-chat-title{
    font-size:13.5px;
    font-weight:600;
    color:rgba(255,255,255,0.85);
    margin-bottom:4px;
}
.empty-chat-desc{
    font-size:11.5px;
    color:rgba(255,255,255,0.45);
    max-width:240px;
    line-height:1.4;
}

/* ── Пузыри сообщений (Modern Cards) ─────────────────────────────────── */
.message{
    max-width:80%;
    padding:10px 14px;
    border-radius:16px;
    word-break:break-word;
    font-size:13px;
    line-height:1.45;
    position:relative;
    box-sizing:border-box;
    transition:transform 0.15s ease, box-shadow 0.15s ease;
}

/* Мои сообщения */
.message.me{
    margin-left:auto;
    background:linear-gradient(135deg, #6c5ce7 0%, #534ab7 100%);
    color:#fff;
    border-radius:16px 16px 4px 16px;
    border:1px solid rgba(255,255,255,0.12);
    box-shadow:0 4px 16px rgba(108,92,231,0.25);
}

/* Сообщения партнёра */
.message.partner{
    margin-right:auto;
    background:#1a1820;
    color:#f1f0f5;
    border-radius:16px 16px 16px 4px;
    border:1px solid rgba(255,255,255,0.08);
    box-shadow:0 4px 14px rgba(0,0,0,0.25);
}

.sender{
    font-size:11px;
    font-weight:600;
    color:#d4537e;
    margin-bottom:4px;
    display:flex;
    align-items:center;
    gap:4px;
}

.msg-text{
    white-space:pre-wrap;
    user-select:text;
}

.msg-text.big-emoji{
    font-size:32px;
    line-height:1.25;
}

.msg-footer{
    display:flex;
    align-items:center;
    justify-content:flex-end;
    gap:4px;
    margin-top:4px;
}

.time{
    font-size:10px;
    color:rgba(255,255,255,0.5);
    font-variant-numeric:tabular-nums;
}
.message.me .time{
    color:rgba(255,255,255,0.7);
}

/* ── Действия над сообщением (Копировать, Ответить) ──────────────────── */
.msg-actions{
    position:absolute;
    top:-12px;
    right:8px;
    display:flex;
    gap:4px;
    opacity:0;
    pointer-events:none;
    transform:translateY(4px);
    transition:opacity 0.15s ease, transform 0.15s ease;
    z-index:5;
}
.message:hover .msg-actions{
    opacity:1;
    pointer-events:auto;
    transform:translateY(0);
}

.action-pill-btn, .msg-copy, .msg-reply{
    width:24px;
    height:24px;
    border-radius:7px;
    border:1px solid rgba(255,255,255,0.12);
    background:rgba(26,24,32,0.92);
    backdrop-filter:blur(8px);
    color:rgba(255,255,255,0.85);
    font-size:11px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    box-shadow:0 4px 12px rgba(0,0,0,0.4);
    transition:all 0.12s ease;
    padding:0;
    -webkit-app-region:no-drag;
}
.action-pill-btn:hover, .msg-copy:hover, .msg-reply:hover{
    background:#6c5ce7;
    color:#fff;
    transform:scale(1.08);
}

/* ── Цитата внутри сообщения (Reply Quote) ───────────────────────────── */
.reply-quote{
    border-left:3px solid rgba(255,255,255,0.45);
    background:rgba(0,0,0,0.22);
    border-radius:8px;
    padding:5px 9px;
    margin-bottom:7px;
    font-size:11.5px;
    backdrop-filter:blur(4px);
}
.message.partner .reply-quote{
    border-left-color:#6c5ce7;
}
.reply-quote-sender{
    color:#c4b5fd;
    font-weight:600;
    margin-bottom:2px;
}
.reply-quote-text{
    color:rgba(255,255,255,0.65);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    max-width:100%;
}

/* ── Плашка "Отвечаете на..." над вводом ─────────────────────────────── */
.reply-preview{
    display:flex;
    flex-shrink:0;
    align-items:center;
    gap:8px;
    padding:7px 12px;
    background:rgba(26,24,32,0.95);
    border-top:1px solid rgba(255,255,255,0.07);
    backdrop-filter:blur(10px);
    -webkit-app-region:no-drag;
}
.reply-preview-body{
    flex:1;
    min-width:0;
    border-left:3px solid #6c5ce7;
    padding-left:8px;
}
.reply-preview-sender{
    font-size:11px;
    font-weight:600;
    color:#a89ef0;
}
.reply-preview-text{
    font-size:11.5px;
    color:rgba(255,255,255,0.55);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.reply-preview-cancel{
    flex-shrink:0;
    width:22px;
    height:22px;
    border:none;
    border-radius:6px;
    background:rgba(255,255,255,0.08);
    color:rgba(255,255,255,0.6);
    cursor:pointer;
    transition:all 0.15s ease;
}
.reply-preview-cancel:hover{
    background:rgba(255,255,255,0.18);
    color:#fff;
}

/* ── Нижняя панель ввода (Dock) ──────────────────────────────────────── */
.input, .input-dock{
    min-height:58px;
    flex-shrink:0;
    max-height:140px;
    background:rgba(20,18,26,0.95);
    backdrop-filter:blur(14px);
    border-top:1px solid rgba(255,255,255,0.07);
    display:flex;
    align-items:flex-end;
    gap:8px;
    padding:9px 12px;
    position:relative;
    -webkit-app-region:no-drag;
}

.input-wrapper{
    flex:1;
    position:relative;
    display:flex;
    align-items:flex-end;
}

.input textarea, .input-dock textarea, .input-wrapper textarea{
    width:100%;
    box-sizing:border-box;
    background:#1a1820;
    border:1px solid rgba(255,255,255,0.08);
    outline:none;
    border-radius:12px;
    padding:8px 48px 8px 12px;
    color:#fff;
    font-family:inherit;
    font-size:13px;
    line-height:20px;
    height:38px;
    min-height:38px;
    max-height:110px;
    resize:none;
    overflow-x:hidden;
    overflow-y:hidden;
    scrollbar-width:none;
    -ms-overflow-style:none;
    transition:border-color 0.15s ease, box-shadow 0.15s ease;
}

.input textarea::-webkit-scrollbar,
.input-dock textarea::-webkit-scrollbar,
.input-wrapper textarea::-webkit-scrollbar{
    width:4px;
    height:4px;
}
.input textarea::-webkit-scrollbar-track,
.input-dock textarea::-webkit-scrollbar-track,
.input-wrapper textarea::-webkit-scrollbar-track{
    background:transparent;
}
.input textarea::-webkit-scrollbar-thumb,
.input-dock textarea::-webkit-scrollbar-thumb,
.input-wrapper textarea::-webkit-scrollbar-thumb{
    background:transparent;
    border-radius:4px;
}
.input textarea::-webkit-scrollbar-button,
.input-dock textarea::-webkit-scrollbar-button,
.input-wrapper textarea::-webkit-scrollbar-button{
    display:none !important;
    width:0 !important;
    height:0 !important;
}

.input-wrapper textarea.has-scroll{
    overflow-y:auto !important;
    scrollbar-width:thin !important;
    scrollbar-color:rgba(255,255,255,0.25) transparent !important;
}

.input-wrapper textarea.has-scroll::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.25) !important;
}

.input-wrapper textarea.has-scroll::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.4) !important;
}

.input textarea:focus, .input-dock textarea:focus, .input-wrapper textarea:focus{
    border-color:rgba(108,92,231,0.6);
    box-shadow:0 0 0 2px rgba(108,92,231,0.2);
}

.char-counter{
    position:absolute;
    right:8px;
    bottom:7px;
    font-size:10px;
    line-height:1;
    color:rgba(255,255,255,0.4);
    background:rgba(26,24,32,0.95);
    padding:2px 5px;
    border-radius:4px;
    pointer-events:none;
    font-variant-numeric:tabular-nums;
    font-weight:500;
    transition:color .15s ease;
}
.char-counter.warn{
    color:#f59e0b;
}
.char-counter.limit{
    color:#ff5277;
    font-weight:700;
}

.dock-btn, .send{
    width:38px;
    height:36px;
    flex-shrink:0;
    border:1px solid rgba(255,255,255,0.08);
    border-radius:11px;
    background:#1a1820;
    color:#fff;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:15px;
    transition:all 0.15s ease;
}

.dock-btn:hover, .emoji-btn:hover{
    background:rgba(255,255,255,0.12);
    border-color:rgba(255,255,255,0.15);
    transform:translateY(-1px);
}

.dock-btn.send-btn, .send:not(.emoji-btn){
    background:linear-gradient(135deg, #6c5ce7 0%, #534ab7 100%);
    border:1px solid rgba(255,255,255,0.15);
    box-shadow:0 4px 14px rgba(108,92,231,0.35);
}

.dock-btn.send-btn:hover, .send:not(.emoji-btn):hover{
    transform:scale(1.05);
    box-shadow:0 6px 18px rgba(108,92,231,0.5);
}

.emoji-btn{
    background:#1a1820;
    font-size:16px;
}

/* ── Панель эмодзи / каомодзи ────────────────────────────────────────── */
.emoji-picker{
    position:fixed;
    left:10px;
    right:10px;
    bottom:64px;
    max-height:270px;
    background:rgba(26,24,32,0.96);
    backdrop-filter:blur(16px);
    border:1px solid rgba(255,255,255,0.12);
    border-radius:14px;
    padding:10px 8px;
    box-shadow:0 12px 36px rgba(0,0,0,0.6);
    overflow-y:auto;
    z-index:30;
}
.emoji-picker::-webkit-scrollbar{
    width:5px;
}
.emoji-picker::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.15);
    border-radius:3px;
}
.emoji-picker::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.25);
}

.emoji-grid{
    display:grid;
    grid-template-columns:repeat(8,1fr);
    gap:3px;
}

.emoji-item{
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:20px;
    padding:6px 0;
    border-radius:8px;
    cursor:pointer;
    user-select:none;
    transition:background 0.12s ease, transform 0.1s ease;
}
.emoji-item:hover{
    background:rgba(255,255,255,0.12);
    transform:scale(1.18);
}

.kaomoji-header{
    font-size:11px;
    font-weight:600;
    color:rgba(255,255,255,0.45);
    text-transform:uppercase;
    letter-spacing:0.6px;
    padding:10px 4px 6px 4px;
    border-top:1px solid rgba(255,255,255,0.08);
    margin-top:8px;
}

.kaomoji-grid{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    padding:2px 0 4px 0;
}

.kaomoji-item{
    background:rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:8px;
    padding:6px 10px;
    color:#e8e6f0;
    font-size:12px;
    cursor:pointer;
    user-select:none;
    transition:all 0.15s ease;
}
.kaomoji-item:hover{
    background:rgba(108,92,231,0.35);
    border-color:rgba(108,92,231,0.5);
    color:#fff;
    transform:scale(1.04);
}

/* ── Модальное окно подтверждения ────────────────────────────────────── */
.confirm-overlay{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,0.6);
    backdrop-filter:blur(4px);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:50;
}

.confirm-box{
    width:calc(100% - 48px);
    max-width:290px;
    background:#1e1c26;
    border:1px solid rgba(255,255,255,0.08);
    border-radius:16px;
    padding:18px;
    box-shadow:0 12px 30px rgba(0,0,0,0.5);
}

.confirm-text{
    font-size:12.5px;
    line-height:1.5;
    color:rgba(255,255,255,0.85);
    margin-bottom:16px;
}

.confirm-btns{
    display:flex;
    gap:8px;
}

.confirm-btn{
    flex:1;
    border:none;
    border-radius:10px;
    padding:8px 0;
    font-size:12px;
    font-weight:500;
    cursor:pointer;
    transition:all 0.15s ease;
}

.confirm-cancel{
    background:rgba(255,255,255,0.08);
    color:rgba(255,255,255,0.7);
}
.confirm-cancel:hover{
    background:rgba(255,255,255,0.14);
    color:#fff;
}

.confirm-ok{
    background:#d4537e;
    color:white;
}
.confirm-ok:hover{
    background:#e84393;
}

/* ── Анимация сердечек ───────────────────────────────────────────────── */
.heart-burst{
    position:fixed;
    inset:0;
    pointer-events:none;
    overflow:hidden;
    z-index:99999;
}
.flying-heart{
    position:absolute;
    font-size:18px;
    animation:flyUp 1.2s ease-out forwards;
}
@keyframes flyUp{
    0%{opacity:1;transform:translateY(0) scale(0.6)}
    50%{opacity:0.9;transform:translateY(-30px) scale(1.2)}
    100%{opacity:0;transform:translateY(-65px) scale(1.5)}
}
@keyframes bannerPop{
    0%{opacity:0;transform:translate(-50%, -20px) scale(0.9)}
    15%{opacity:1;transform:translate(-50%, 0) scale(1.05)}
    25%{opacity:1;transform:translate(-50%, 0) scale(1)}
    85%{opacity:1;transform:translate(-50%, 0) scale(1)}
    100%{opacity:0;transform:translate(-50%, -15px) scale(0.95)}
}
.heart-banner{
    position:fixed;
    top:54px;
    left:50%;
    transform:translateX(-50%);
    background:rgba(212,83,126,0.95);
    backdrop-filter:blur(8px);
    color:#fff;
    padding:8px 18px;
    border-radius:24px;
    font-size:13px;
    font-weight:600;
    display:flex;
    align-items:center;
    gap:8px;
    box-shadow:0 8px 24px rgba(212,83,126,0.45);
    z-index:999999;
    pointer-events:none;
    animation:bannerPop 3.2s ease-in-out forwards;
}
"""
