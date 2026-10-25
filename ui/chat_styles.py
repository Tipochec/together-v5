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
    font-family:-apple-system,'Segoe UI',sans-serif;
    height:100vh;
    overflow:hidden;
    -webkit-app-region:no-drag;
    display:flex;
    flex-direction:column;
}

.titlebar{
    height:40px;
    flex-shrink:0;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 14px;
    border-bottom:.5px solid rgba(255,255,255,.06);
    -webkit-app-region:drag;
}

.title{
    color:#d4537e;
    font-size:14px;
}

.close{
    width:28px;
    height:28px;
    border:none;
    border-radius:6px;
    background:transparent;
    color:rgba(255,255,255,.4);
    cursor:pointer;
    -webkit-app-region:no-drag;
}

.close:hover{
    background:rgba(255,255,255,.08);
}

.messages{
    flex:1;
    min-height:0;
    overflow-y:auto;
    padding:14px;
}

.messages::-webkit-scrollbar{
    width:6px;
}
.messages::-webkit-scrollbar-track{
    background:transparent;
}
.messages::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.12);
    border-radius:10px;
}
.messages::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.2);
}

.input{
    min-height:55px;
    flex-shrink:0;
    max-height:140px;
    border-top:.5px solid rgba(255,255,255,.06);
    display:flex;
    align-items:flex-end;
    gap:8px;
    padding:10px;
}

.input-wrapper{
    flex:1;
    position:relative;
    display:flex;
    align-items:flex-end;
}

.input textarea, .input-wrapper textarea{
    width:100%;
    box-sizing:border-box;
    background:#1a1820;
    border:none;
    outline:none;
    border-radius:10px;
    padding:8px 48px 8px 12px;
    color:white;
    font-family:inherit;
    font-size:13px;
    line-height:1.4;
    resize:none;
    max-height:120px;
    overflow-y:auto;
}

.char-counter{
    position:absolute;
    right:8px;
    bottom:7px;
    font-size:10px;
    line-height:1;
    color:rgba(255,255,255,0.4);
    background:rgba(26,24,32,0.92);
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

.send{
    width:42px;
    height:38px;
    flex-shrink:0;
    border:none;
    border-radius:10px;
    background:#534ab7;
    color:white;
    cursor:pointer;
}

.emoji-btn{
    background:#1a1820;
    font-size:16px;
}
.emoji-btn:hover{
    background:#232030;
}

.emoji-picker{
    position:fixed;
    left:10px;
    right:10px;
    bottom:65px;
    height:280px;
    background:#1a1820;
    border:0.5px solid rgba(255,255,255,0.12);
    border-radius:12px;
    padding:0;
    box-shadow:0 8px 26px rgba(0,0,0,0.55);
    display:flex;
    flex-direction:column;
    z-index:20;
    overflow:hidden;
}

.emoji-tabs{
    display:flex;
    gap:4px;
    padding:8px 8px 6px 8px;
    border-bottom:0.5px solid rgba(255,255,255,0.08);
    background:rgba(0,0,0,0.25);
    overflow-x:auto;
    scrollbar-width:none;
    flex-shrink:0;
}
.emoji-tabs::-webkit-scrollbar{
    display:none;
}

.emoji-tab{
    background:rgba(255,255,255,0.05);
    border:0.5px solid rgba(255,255,255,0.08);
    border-radius:8px;
    padding:4px 8px;
    color:rgba(255,255,255,0.65);
    font-size:11px;
    cursor:pointer;
    white-space:nowrap;
    transition:all 0.15s ease;
    flex-shrink:0;
}
.emoji-tab:hover{
    background:rgba(255,255,255,0.1);
    color:#fff;
}
.emoji-tab.active{
    background:#534ab7;
    border-color:#6c5ce7;
    color:#fff;
    font-weight:600;
}

.emoji-body{
    flex:1;
    overflow-y:auto;
    padding:8px 6px;
}
.emoji-body::-webkit-scrollbar{
    width:5px;
}
.emoji-body::-webkit-scrollbar-thumb{
    background:rgba(255,255,255,0.15);
    border-radius:3px;
}
.emoji-body::-webkit-scrollbar-thumb:hover{
    background:rgba(255,255,255,0.25);
}

.emoji-grid{
    display:grid;
    grid-template-columns:repeat(8,1fr);
    gap:2px;
}

.emoji-item{
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:20px;
    line-height:1;
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

.kaomoji-grid{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    padding:2px;
}

.kaomoji-item{
    background:rgba(255,255,255,0.06);
    border:0.5px solid rgba(255,255,255,0.08);
    border-radius:8px;
    padding:6px 10px;
    color:#e8e6f0;
    font-size:12px;
    cursor:pointer;
    user-select:none;
    transition:all 0.15s ease;
}
.kaomoji-item:hover{
    background:rgba(83,74,183,0.35);
    border-color:rgba(108,92,231,0.5);
    color:#fff;
    transform:scale(1.04);
}

.message{
    max-width:75%;
    padding:10px 54px 10px 14px;
    border-radius:14px;
    margin-bottom:8px;
    word-break:break-word;
    font-size:13px;
    position:relative;
}

.msg-text{
    white-space:pre-wrap;
    user-select:text;
}

.msg-text.big-emoji{
    font-size:32px;
    line-height:1.2;
}

.msg-copy{
    position:absolute;
    top:6px;
    right:6px;
    width:20px;
    height:20px;
    border:none;
    border-radius:5px;
    background:rgba(0,0,0,0.25);
    color:rgba(255,255,255,0.75);
    font-size:11px;
    line-height:1;
    cursor:pointer;
    display:none;
    align-items:center;
    justify-content:center;
    padding:0;
    -webkit-app-region:no-drag;
}
.message:hover .msg-copy{
    display:flex;
}
.msg-copy:hover{
    background:rgba(0,0,0,0.4);
    color:#fff;
}

.msg-reply{
    position:absolute;
    top:6px;
    right:30px;
    width:20px;
    height:20px;
    border:none;
    border-radius:5px;
    background:rgba(0,0,0,0.25);
    color:rgba(255,255,255,0.75);
    font-size:12px;
    line-height:1;
    cursor:pointer;
    display:none;
    align-items:center;
    justify-content:center;
    padding:0;
    -webkit-app-region:no-drag;
}
.message:hover .msg-reply{
    display:flex;
}
.msg-reply:hover{
    background:rgba(0,0,0,0.4);
    color:#fff;
}

/* Цитата внутри самого пузыря сообщения — то, на что ответили */
.reply-quote{
    border-left:3px solid rgba(255,255,255,0.3);
    background:rgba(0,0,0,0.15);
    border-radius:6px;
    padding:4px 8px;
    margin-bottom:6px;
    font-size:11.5px;
}
.reply-quote-sender{
    color:#a89ef0;
    font-weight:600;
    margin-bottom:1px;
}
.reply-quote-text{
    color:rgba(255,255,255,0.55);
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    max-width:100%;
}

/* Плашка "отвечаете на..." над полем ввода, пока ответ не отправлен/не отменён */
.reply-preview{
    display:flex;
    flex-shrink:0;
    align-items:center;
    gap:8px;
    padding:6px 10px;
    background:#1a1820;
    border-top:.5px solid rgba(255,255,255,.06);
    -webkit-app-region:no-drag;
}
.reply-preview-body{
    flex:1;
    min-width:0;
    border-left:3px solid #534ab7;
    padding-left:8px;
}
.reply-preview-sender{
    font-size:11px;
    font-weight:600;
    color:#a89ef0;
}
.reply-preview-text{
    font-size:11.5px;
    color:rgba(255,255,255,0.5);
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
}
.reply-preview-cancel:hover{
    background:rgba(255,255,255,0.15);
}

.sender{
    font-size:11px;
    font-weight:600;
    margin-bottom:3px;
    color:#a89ef0;
}

.message.me{
    margin-left:auto;
    background:#534ab7;
}

.message.partner{
    margin-right:auto;
    background:#1a1820;
}

.time{
    margin-top:4px;
    font-size:10px;
    opacity:.5;
}

.confirm-overlay{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,0.55);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:50;
}

.confirm-box{
    width:calc(100% - 48px);
    max-width:280px;
    background:#1e1c26;
    border:0.5px solid rgba(255,255,255,0.08);
    border-radius:14px;
    padding:16px;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
}

.confirm-text{
    font-size:12.5px;
    line-height:1.5;
    color:rgba(255,255,255,0.8);
    margin-bottom:14px;
}

.confirm-btns{
    display:flex;
    gap:8px;
}

.confirm-btn{
    flex:1;
    border:none;
    border-radius:9px;
    padding:8px 0;
    font-size:12px;
    cursor:pointer;
}

.confirm-cancel{
    background:rgba(255,255,255,0.08);
    color:rgba(255,255,255,0.6);
}

.confirm-ok{
    background:#d4537e;
    color:white;
}

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
    top:48px;
    left:50%;
    transform:translateX(-50%);
    background:rgba(212,83,126,0.95);
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
