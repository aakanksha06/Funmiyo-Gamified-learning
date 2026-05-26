/**
 * Funmiyo SkillQuest — Adaptive Engine
 * Kid-friendly adaptive difficulty for KG–Grade 5
 */
class AdaptiveEngine {
  constructor(gameType) {
    this.gameType = gameType;
    this.mode = 'easy';
    this.serverProfile = null;
    this.window = [];
    this.windowSize = 15;
    this.adaptiveLevel = 0;       // 0=easiest .. 2=hardest
    this.consecutiveCorrect = 0;
    this.consecutiveWrong = 0;
    this.reactionTimes = [];
    this.avgReactionTime = 8.0;
    this.PROMOTE = 3;             // correct streak before harder
    this.DEMOTE  = 2;             // wrong streak before easier (gentler for kids)
    this.onLevelChange = null;
    this.onFeedback    = null;
    this.grade = 'KG';
  }

  async loadProfile() {
    try {
      const res = await fetch('/api/adaptive/settings');
      this.serverProfile = await res.json();
      this.grade = this.serverProfile.grade || 'KG';
      if (this.mode === 'adaptive' && this.serverProfile.difficulty) {
        this.adaptiveLevel = { easy:0, medium:1, hard:2 }[this.serverProfile.difficulty] ?? 0;
      }
    } catch (e) { this.serverProfile = null; }
    return this.serverProfile;
  }

  async loadGradeConfig() {
    try {
      const res = await fetch('/api/grade/config');
      return await res.json();
    } catch (e) { return { ops:['+'], max_num:5, time:120 }; }
  }

  record(correct, reactionTime) {
    this.window.push({ correct, reactionTime, ts: Date.now() });
    if (this.window.length > this.windowSize) this.window.shift();
    if (reactionTime > 0 && reactionTime < 60) {
      this.reactionTimes.push(reactionTime);
      if (this.reactionTimes.length > 12) this.reactionTimes.shift();
      this.avgReactionTime = this.reactionTimes.reduce((a,b)=>a+b,0) / this.reactionTimes.length;
    }
    if (correct) { this.consecutiveCorrect++; this.consecutiveWrong = 0; }
    else         { this.consecutiveWrong++;   this.consecutiveCorrect = 0; }
    if (this.mode !== 'adaptive') return null;
    return this._evaluate();
  }

  _evaluate() {
    if (this.window.length < 4) return null;
    const recent   = this.window.slice(-8);
    const accuracy = recent.filter(a=>a.correct).length / recent.length;
    let reason = null, feedback = null;

    if (this.consecutiveCorrect >= this.PROMOTE && accuracy >= 0.75) {
      this.adaptiveLevel = Math.min(2, this.adaptiveLevel + 0.5);
      this.consecutiveCorrect = 0;
      reason = 'promote'; feedback = this._praise();
    } else if (this.consecutiveWrong >= this.DEMOTE || accuracy < 0.30) {
      this.adaptiveLevel = Math.max(0, this.adaptiveLevel - 0.5);
      this.consecutiveWrong = 0;
      reason = 'demote'; feedback = this._encourage();
    } else if (accuracy >= 0.88 && this.window.length >= 8) {
      this.adaptiveLevel = Math.min(2, this.adaptiveLevel + 0.25);
      reason = 'sustain_high';
    } else if (accuracy < 0.45 && this.window.length >= 8) {
      this.adaptiveLevel = Math.max(0, this.adaptiveLevel - 0.25);
      reason = 'sustain_low';
    }

    if (reason && this.onLevelChange) {
      const s = this.getCurrentSettings();
      this.onLevelChange(s, reason, feedback);
      return { settings:s, reason, feedback };
    }
    return null;
  }

  getCurrentSettings() {
    const lvl = this.adaptiveLevel;
    const t   = lvl / 2;
    const gc  = this.serverProfile || {};
    const ops_by_level = {
      'KG':      [['+'], ['+'], ['+']],
      'Grade 1': [['+'], ['+'], ['+']],
      'Grade 2': [['+'], ['+','-'], ['+','-']],
      'Grade 3': [['+','-'], ['+','-'], ['+','-']],
      'Grade 4': [['+','-'], ['+','-','×'], ['+','-','×']],
      'Grade 5': [['+','-','×'], ['+','-','×'], ['+','-','×','÷']],
    };
    const gradeOps = ops_by_level[this.grade] || ops_by_level['KG'];
    const opIdx    = Math.min(2, Math.floor(lvl));
    return {
      mode:           'adaptive',
      adaptiveLevel:  lvl,
      difficultyLabel: this._label(lvl),
      operators:      gradeOps[opIdx],
      numMin: 1,
      numMax:         Math.round(lerp(gc.max_num ? gc.max_num*0.4 : 3, gc.max_num || 10, t)),
      timeLimit:      Math.round(lerp(gc.time ? gc.time*1.3 : 120, gc.time || 90, t)),
      speedMultiplier:lerp(0.6, 1.2, t),
      hintLevel:      lvl < 0.6 ? 3 : lvl < 1.3 ? 2 : 1,
      scoreMultiplier:lerp(1, 2, t),
      targetMin:      1,
      targetMax:      Math.round(lerp(gc.max_num ? gc.max_num*0.5 : 5, gc.max_num || 10, t)),
      shots:          20,
      bossAttackInterval: Math.round(lerp(9000, 5000, t)),
      accuracy:       this.windowAccuracy(),
      avgReaction:    Math.round(this.avgReactionTime * 10) / 10,
    };
  }

  getFixedSettings(mode) {
    const gc = this.serverProfile || { ops:['+'], max_num:10, time:90 };
    const presets = {
      easy: {
        mode:'easy', adaptiveLevel:0, difficultyLabel:'Easy 😊',
        operators:gc.ops?[gc.ops[0]]:['+'],
        numMin:1, numMax:Math.ceil((gc.max_num||10)*0.5),
        timeLimit:Math.round((gc.time||90)*1.4), speedMultiplier:0.6,
        hintLevel:3, scoreMultiplier:1, targetMin:1,
        targetMax:Math.ceil((gc.max_num||10)*0.5),
        shots:25, bossAttackInterval:9000,
      },
      medium: {
        mode:'medium', adaptiveLevel:1, difficultyLabel:'Medium 🌟',
        operators:gc.ops||['+'],
        numMin:1, numMax:gc.max_num||10,
        timeLimit:gc.time||90, speedMultiplier:0.9,
        hintLevel:2, scoreMultiplier:1.5, targetMin:1,
        targetMax:gc.max_num||10,
        shots:20, bossAttackInterval:7000,
      },
      hard: {
        mode:'hard', adaptiveLevel:2, difficultyLabel:'Hard 🔥',
        operators:gc.ops||['+'],
        numMin:1, numMax:gc.max_num||10,
        timeLimit:Math.round((gc.time||90)*0.75), speedMultiplier:1.2,
        hintLevel:1, scoreMultiplier:2, targetMin:1,
        targetMax:gc.max_num||10,
        shots:15, bossAttackInterval:5000,
      },
    };
    return presets[mode] || presets.easy;
  }

  windowAccuracy() {
    if (!this.window.length) return 0;
    return Math.round(this.window.filter(a=>a.correct).length / this.window.length * 100);
  }
  _label(lvl) { return lvl<0.6?'Easy 😊':lvl<1.2?'Medium 🌟':lvl<1.7?'Hard 🔥':'Super Hard 🚀'; }
  _praise() {
    const m=['🌟 Amazing! Getting harder!','⭐ You\'re a star! Level up!','🎉 Brilliant! More challenge!','🚀 Superstar! Keep going!'];
    return m[Math.floor(Math.random()*m.length)];
  }
  _encourage() {
    const m=['💪 You can do it! Easier now!','😊 Let\'s try easier ones!','🌈 No worries! You\'ve got this!','🤗 Almost there! Easier mode!'];
    return m[Math.floor(Math.random()*m.length)];
  }
}

function lerp(a, b, t) { return a + (b-a)*Math.max(0,Math.min(1,t)); }

/* ── Adaptive HUD ── */
function createAdaptiveHUD(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div id="adaptiveHUD" style="display:none;position:fixed;top:76px;right:14px;z-index:80;
      background:rgba(13,15,43,0.94);border:2px solid rgba(255,215,0,0.3);border-radius:16px;
      padding:12px 16px;backdrop-filter:blur(16px);min-width:176px;pointer-events:none;">
      <div style="font-family:'Fredoka One',cursive;font-size:0.75rem;color:rgba(255,255,255,0.5);margin-bottom:8px;">🤖 AI Mode</div>
      <div style="font-family:'Fredoka One',cursive;font-size:1rem;color:#ffd700;margin-bottom:6px;" id="adaptLevelLabel">Easy 😊</div>
      <div style="height:8px;background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;margin-bottom:6px;">
        <div id="adaptLevelBar" style="height:100%;border-radius:4px;background:linear-gradient(90deg,#00e676,#ffd700);width:0%;transition:width 0.6s ease;"></div>
      </div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.45);">Correct: <span id="adaptAcc" style="color:#00e676">—</span></div>
    </div>
    <div id="adaptFeedback" style="display:none;position:fixed;top:50%;left:50%;
      transform:translate(-50%,-50%) scale(0);font-family:'Fredoka One',cursive;
      font-size:1.6rem;color:#ffd700;text-shadow:0 0 30px rgba(255,215,0,0.8);
      pointer-events:none;z-index:600;text-align:center;white-space:nowrap;"></div>`;
  if (!document.getElementById('adaptKF')) {
    const s = document.createElement('style'); s.id = 'adaptKF';
    s.textContent = `@keyframes adaptFeedAnim{0%{transform:translate(-50%,-50%) scale(0);opacity:1}20%{transform:translate(-50%,-54%) scale(1.15);opacity:1}70%{transform:translate(-50%,-54%) scale(1);opacity:1}100%{transform:translate(-50%,-68%) scale(0.8);opacity:0}}`;
    document.head.appendChild(s);
  }
}

function updateAdaptiveHUD(settings) {
  const hud = document.getElementById('adaptiveHUD');
  if (!hud) return;
  if (settings.mode !== 'adaptive') { hud.style.display='none'; return; }
  hud.style.display = 'block';
  const pct = (settings.adaptiveLevel/2)*100;
  const lbl = document.getElementById('adaptLevelLabel');
  const bar = document.getElementById('adaptLevelBar');
  const acc = document.getElementById('adaptAcc');
  if (lbl) lbl.textContent = settings.difficultyLabel || 'Easy 😊';
  if (bar) bar.style.width = pct+'%';
  if (acc) acc.textContent = settings.accuracy!=null ? settings.accuracy+'%' : '—';
}

function showAdaptFeedback(msg) {
  const el = document.getElementById('adaptFeedback');
  if (!el) return;
  el.textContent = msg; el.style.display = 'block';
  el.style.animation = 'none'; void el.offsetWidth;
  el.style.animation = 'adaptFeedAnim 2.4s cubic-bezier(0.16,1,0.3,1) forwards';
}