
'use strict';
const canvas=document.getElementById('gameCanvas'),ctx=canvas.getContext('2d');
let W,H;
function resize(){W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight;}
resize();window.addEventListener('resize',resize);

const ai=new AdaptiveEngine('blaster');
ai.onLevelChange=(s,reason,fb)=>{applySettings(s);updateAdaptiveHUD(s);if(fb)showAdaptFeedback(fb);};

let gradeConfig={ops:['+'],max_num:10,time:100};
let currentMode='easy',cfg={};
function buildCfg(s){return{ops:s.operators||['+'],numRange:[s.numMin||1,s.numMax||10],speed:s.speedMultiplier||.6,spawnRate:Math.max(60,180-Math.round((s.adaptiveLevel||0)*30)),maxEnemies:2+Math.round(s.adaptiveLevel||0),lives:3,timeBonus:s.timeBonus||25};}
function applySettings(s){cfg=buildCfg(s);lives=cfg.lives;renderLives();}
function setMode(m){currentMode=m;ai.mode=m;document.querySelectorAll('.mode-pill').forEach(el=>el.classList.toggle('active',el.classList.contains(m)));const s=m==='adaptive'?ai.getCurrentSettings():ai.getFixedSettings(m);applySettings(s);updateAdaptiveHUD(s);}

let sessionId=null,sessionStart=Date.now(),lastActionTime=Date.now();
let score=0,wave=1,lives=3,streak=0,bestStreak=0;
let totalShots=0,correctShots=0,waveKills=0,waveTarget=6;
let gameActive=false,betweenWaves=false,frameCount=0;
let operatorCounts={},shakeFrames=0;
let ship=null,enemies=[],bullets=[],particles=[],explosions=[],stars=[];
let currentEq=null,answerOptions=[];

function initShip(){ship={x:W/2,y:H-160,vx:0,tLeft:false,tRight:false,inv:0};}
function initStars(){stars=[];for(let i=0;i<160;i++)stars.push({x:Math.random()*W,y:Math.random()*H,sz:Math.random()*2.2+.3,spd:Math.random()*.7+.1,brt:Math.random()});}

// Kid-friendly enemy shapes with faces
function makeEnemy(){
  const op=cfg.ops[Math.floor(Math.random()*cfg.ops.length)];
  const [mn,mx]=cfg.numRange;
  let a=randInt(mn,mx),b=randInt(mn,mx),answer;
  if(op==='-'&&a<b){const t=a;a=b;b=t;}
  if(op==='÷'){b=randInt(1,Math.min(5,mx));a=b*randInt(1,Math.min(mx,8));if(a>99)a=b*randInt(1,4);}
  switch(op){case'+':answer=a+b;break;case'-':answer=a-b;break;case'×':answer=a*b;break;case'÷':answer=a/b;break;default:answer=a+b;}
  const lane=Math.floor(Math.random()*5),laneW=W/5;
  const ex=Math.max(55,Math.min(W-55,laneW*lane+laneW/2+(Math.random()-.5)*30));
  const alienFaces=['👾','🛸','👽','🤖','👻','🦄'];
  return{x:ex,y:-65,a,b,op,answer,eq:`${a} ${op} ${b} = ?`,w:100,h:50,
    speed:cfg.speed*(0.7+Math.random()*.5)*(1+wave*.05),hp:wave>4?2:1,
    id:Math.random(),phase:Math.random()*Math.PI*2,type:Math.floor(Math.random()*alienFaces.length),
    face:alienFaces[Math.floor(Math.random()*alienFaces.length)],hitAnim:0,active:true};
}

function pickEq(){
  const alive=enemies.filter(e=>e.active);
  if(!alive.length){clearBar();return;}
  alive.sort((a,b)=>b.y-a.y);
  const tgt=alive[0];
  if(currentEq&&currentEq.id===tgt.id)return;
  currentEq=tgt;buildOpts(tgt);
}

function buildOpts(e){
  const c=e.answer,opts=new Set([c]);
  const deltas=[-3,-2,-1,1,2,3,4,-4,5,-5,6,-6];shuffle(deltas);
  for(const d of deltas){if(opts.size>=4)break;const w=c+d;if(w>=0&&w!==c)opts.add(w);}
  while(opts.size<4)opts.add(c+randInt(5,12)*(Math.random()<.5?1:-1));
  answerOptions=shuffle([...opts]).slice(0,4);renderBar(e);
}

function renderBar(e){
  document.getElementById('eqShow').textContent=e.eq+' 🤔';
  const bar=document.getElementById('ansBtns');bar.innerHTML='';
  const palettes=[
    {border:'#4ecdc4',bg:'rgba(78,205,196,.15)',c:'#4ecdc4'},
    {border:'#ff4db8',bg:'rgba(255,77,184,.15)',c:'#ff4db8'},
    {border:'#ffd700',bg:'rgba(255,215,0,.15)',c:'#ffd700'},
    {border:'#a855f7',bg:'rgba(168,85,247,.15)',c:'#a855f7'},
  ];
  answerOptions.forEach((val,i)=>{
    const btn=document.createElement('button');
    btn.className='ans-btn';btn.textContent=val;
    const p=palettes[i%palettes.length];
    btn.style.cssText=`border-color:${p.border};background:${p.bg};color:${p.c};box-shadow:0 4px 16px ${p.bg};`;
    btn.addEventListener('click',()=>handleAns(val,btn));
    bar.appendChild(btn);
  });
}
function clearBar(){document.getElementById('eqShow').textContent='👾 Cleared! More coming...';document.getElementById('ansBtns').innerHTML='';currentEq=null;}

function handleAns(val,btn){
  if(!gameActive||!currentEq)return;
  totalShots++;const rt=(Date.now()-lastActionTime)/1000;lastActionTime=Date.now();
  const correct=val===currentEq.answer;ai.record(correct,rt);
  if(correct){
    correctShots++;streak++;if(streak>bestStreak)bestStreak=streak;
    const pts=100+(cfg.timeBonus||25)+(wave*8);score+=pts;waveKills++;
    operatorCounts[currentEq.op]=(operatorCounts[currentEq.op]||0)+1;
    btn.classList.add('correct');setTimeout(()=>btn.classList.remove('correct'),400);
    fireBullet(currentEq);showScorePop(pts);
    if(streak>=3)announceWave(`🔥 ${streak} in a row!`);
    logAction({action_type:'shoot',success:true,operator_used:currentEq.op,operand1:currentEq.a,operand2:currentEq.b,target_value:currentEq.answer,result_value:val,reaction_time:rt,score_delta:pts,combo_count:streak});
  }else{
    streak=0;btn.classList.add('wrong');setTimeout(()=>btn.classList.remove('wrong'),400);
    shakeFrames=8;
    logAction({action_type:'shoot',success:false,operator_used:currentEq?.op,target_value:currentEq?.answer,result_value:val,reaction_time:rt});
  }
  updateHUD();
  if(waveKills>=waveTarget&&!betweenWaves)advanceWave();
}

function advanceWave(){betweenWaves=true;setTimeout(()=>{wave++;waveKills=0;waveTarget=5+wave*2;enemies=[];announceWave(`🌊 Wave ${wave}!`);betweenWaves=false;updateHUD();},1400);}

function fireBullet(e){bullets.push({x:ship.x,y:ship.y-22,tx:e.x,ty:e.y,targetId:e.id,speed:15,trail:[],active:true});}

function explodeEnemy(ex,ey){
  for(let i=0;i<16;i++){const a=(Math.PI*2/16)*i+Math.random()*.4,spd=2+Math.random()*5;particles.push({x:ex,y:ey,vx:Math.cos(a)*spd,vy:Math.sin(a)*spd,life:1,size:3+Math.random()*5,color:['#ffd700','#ff6b35','#ff4db8','#4ecdc4'][Math.floor(Math.random()*4)],decay:.025+Math.random()*.02});}
  explosions.push({x:ex,y:ey,r:10,maxR:70,life:1,color:'#ffd700'});
}

function renderLives(){
  const c=document.getElementById('livesRow');c.innerHTML='';
  for(let i=0;i<cfg.lives||3;i++){const s=document.createElement('span');s.className='life'+(i>=lives?' lost':'');s.textContent='❤️';c.appendChild(s);}
}
function loseLife(){lives--;renderLives();ship.inv=100;shakeFrames=12;if(lives<=0)setTimeout(()=>endGame('dead'),400);}
function updateHUD(){document.getElementById('hudScore').textContent=score.toLocaleString();document.getElementById('hudWave').textContent=wave;document.getElementById('hudStreak').textContent=streak;document.getElementById('hudAcc').textContent=totalShots>0?Math.round(correctShots/totalShots*100)+'%':'—';}
function announceWave(t){const el=document.getElementById('waveAnn');el.textContent=t;el.classList.remove('show');void el.offsetWidth;el.classList.add('show');}

function showScorePop(pts){const div=document.createElement('div');div.style.cssText=`position:fixed;left:${W/2}px;top:${H*.42}px;transform:translateX(-50%);font-family:'Fredoka One',cursive;font-size:1.4rem;color:#ffd700;text-shadow:0 0 14px rgba(255,215,0,.8);pointer-events:none;z-index:80;animation:scorePop 1s ease-out forwards;`;div.textContent='+'+pts;document.body.appendChild(div);setTimeout(()=>div.remove(),1000);}

// Draw functions
function drawBg(){ctx.fillStyle='#080b1e';ctx.fillRect(0,0,W,H);for(const s of stars){s.y+=s.spd;if(s.y>H){s.y=0;s.x=Math.random()*W;}ctx.globalAlpha=s.brt*(0.5+Math.sin(frameCount*.02+s.x)*.3);ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(s.x,s.y,s.sz,0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;}

function drawShip(){
  if(!ship)return;const{x,y,inv}=ship;
  if(inv>0&&Math.floor(inv/6)%2===0)return;
  ctx.save();ctx.translate(x,y);
  // Engine glow
  const eg=ctx.createRadialGradient(0,26,2,0,28,22);eg.addColorStop(0,'rgba(78,205,196,.9)');eg.addColorStop(1,'transparent');ctx.fillStyle=eg;ctx.beginPath();ctx.ellipse(0,28+Math.sin(frameCount*.3)*3,10,16,0,0,Math.PI*2);ctx.fill();
  ctx.shadowColor='#4ecdc4';ctx.shadowBlur=16;
  // Ship body
  ctx.fillStyle='#0d2535';ctx.beginPath();ctx.moveTo(0,-24);ctx.lineTo(-18,16);ctx.lineTo(-7,8);ctx.lineTo(0,12);ctx.lineTo(7,8);ctx.lineTo(18,16);ctx.closePath();ctx.fill();
  const sg=ctx.createLinearGradient(-18,-24,18,16);sg.addColorStop(0,'rgba(78,205,196,.6)');sg.addColorStop(1,'rgba(0,100,150,.3)');ctx.fillStyle=sg;ctx.beginPath();ctx.moveTo(0,-24);ctx.lineTo(-18,16);ctx.lineTo(-7,8);ctx.lineTo(0,12);ctx.lineTo(7,8);ctx.lineTo(18,16);ctx.closePath();ctx.fill();
  // Cockpit
  ctx.fillStyle='rgba(255,215,0,.8)';ctx.beginPath();ctx.ellipse(0,-7,5,8,0,0,Math.PI*2);ctx.fill();
  ctx.restore();
}

function drawEnemy(e){
  if(!e.active)return;
  ctx.save();ctx.translate(e.x,e.y+Math.sin(frameCount*.04+e.phase)*4);
  if(e.hitAnim>0){ctx.globalAlpha=.5+e.hitAnim*.5;e.hitAnim-=.1;}
  // Alien body glow
  const gg=ctx.createRadialGradient(0,0,10,0,0,e.w*.6);gg.addColorStop(0,'rgba(255,215,0,.15)');gg.addColorStop(1,'transparent');ctx.fillStyle=gg;ctx.beginPath();ctx.arc(0,0,e.w*.6,0,Math.PI*2);ctx.fill();
  // Alien face emoji
  ctx.shadowColor='#ffd700';ctx.shadowBlur=14;
  ctx.font=`${e.h*.8}px sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(e.face,0,-2);
  // Equation text
  ctx.shadowBlur=0;ctx.fillStyle='#fff';ctx.font=`bold 13px 'Fredoka One',cursive`;ctx.textAlign='center';ctx.textBaseline='middle';
  // Badge bg
  ctx.fillStyle='rgba(13,15,43,.8)';ctx.beginPath();ctx.roundRect(-e.w*.48,e.h*.3,e.w*.96,22,8);ctx.fill();
  ctx.fillStyle='#ffd700';ctx.fillText(e.eq,0,e.h*.42);
  if(e.hp>1){ctx.strokeStyle='rgba(255,255,255,.4)';ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(0,0,e.w*.5,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}
  ctx.restore();
}

function drawBullets(){
  for(const b of bullets){
    if(!b.active)continue;
    b.trail.push({x:b.x,y:b.y});if(b.trail.length>10)b.trail.shift();
    for(let i=0;i<b.trail.length-1;i++){const a=i/b.trail.length;ctx.globalAlpha=a*.5;ctx.strokeStyle='#4ecdc4';ctx.lineWidth=3*a;ctx.shadowColor='#4ecdc4';ctx.shadowBlur=8;ctx.beginPath();ctx.moveTo(b.trail[i].x,b.trail[i].y);ctx.lineTo(b.trail[i+1].x,b.trail[i+1].y);ctx.stroke();}
    ctx.globalAlpha=1;ctx.shadowBlur=0;
    ctx.save();ctx.shadowColor='#ffd700';ctx.shadowBlur=18;ctx.fillStyle='#ffd700';ctx.beginPath();ctx.arc(b.x,b.y,6,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(b.x,b.y,3,0,Math.PI*2);ctx.fill();ctx.restore();
  }
}

function drawParticles(){for(const p of particles){ctx.save();ctx.globalAlpha=p.life;ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=8;ctx.beginPath();ctx.arc(p.x,p.y,p.size*p.life,0,Math.PI*2);ctx.fill();ctx.restore();}}
function drawExplosions(){for(const ex of explosions){ctx.save();ctx.globalAlpha=ex.life*.55;const g=ctx.createRadialGradient(ex.x,ex.y,0,ex.x,ex.y,ex.r);g.addColorStop(0,'#fff');g.addColorStop(.3,ex.color);g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.beginPath();ctx.arc(ex.x,ex.y,ex.r,0,Math.PI*2);ctx.fill();ctx.restore();}}
function drawDangerLine(){const ly=H-130;ctx.save();ctx.strokeStyle='rgba(255,107,53,.15)';ctx.lineWidth=1;ctx.setLineDash([8,8]);ctx.beginPath();ctx.moveTo(0,ly);ctx.lineTo(W,ly);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='rgba(255,107,53,.08)';ctx.fillRect(0,ly,W,H-ly);ctx.restore();}

function update(){
  if(!gameActive)return;frameCount++;
  if(ship){if(ship.tLeft)ship.vx=Math.max(ship.vx-.8,-7);if(ship.tRight)ship.vx=Math.min(ship.vx+.8,7);if(!ship.tLeft&&!ship.tRight)ship.vx*=.88;ship.x=Math.max(28,Math.min(W-28,ship.x+ship.vx));if(ship.inv>0)ship.inv--;}
  if(!betweenWaves&&frameCount%Math.max(45,cfg.spawnRate-wave*8)===0&&enemies.filter(e=>e.active).length<cfg.maxEnemies+Math.floor(wave/3))enemies.push(makeEnemy());
  for(const e of enemies){if(!e.active)continue;e.y+=e.speed;e.x+=Math.sin(frameCount*.02+e.id*8)*.35;e.x=Math.max(55,Math.min(W-55,e.x));if(e.y>H-110){e.active=false;if(ship&&ship.inv===0)loseLife();}}
  for(const b of bullets){if(!b.active)continue;const dx=b.tx-b.x,dy=b.ty-b.y,dist=Math.hypot(dx,dy);if(dist<b.speed){const t=enemies.find(e=>e.id===b.targetId&&e.active);if(t){t.hp--;t.hitAnim=1;if(t.hp<=0){t.active=false;explodeEnemy(t.x,t.y);score+=50+wave*5;waveKills++;updateHUD();currentEq=null;setTimeout(pickEq,120);if(waveKills>=waveTarget&&!betweenWaves)advanceWave();}}b.active=false;}else{b.x+=(dx/dist)*b.speed;b.y+=(dy/dist)*b.speed;}}
  for(const p of particles){p.x+=p.vx;p.y+=p.vy;p.vy+=.1;p.vx*=.97;p.life-=p.decay;}
  for(const ex of explosions){ex.r+=4;ex.life-=.08;}
  enemies=enemies.filter(e=>e.active);bullets=bullets.filter(b=>b.active);particles=particles.filter(p=>p.life>0);explosions=explosions.filter(ex=>ex.life>0);
  pickEq();
}

function gameLoop(){
  if(shakeFrames>0){ctx.save();ctx.translate((Math.random()-.5)*7,(Math.random()-.5)*7);shakeFrames--;}
  drawBg();drawDangerLine();drawExplosions();enemies.forEach(drawEnemy);drawBullets();drawParticles();drawShip();
  if(shakeFrames>=0){try{ctx.restore();}catch(e){}}
  update();requestAnimationFrame(gameLoop);
}

document.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')ship&&(ship.tLeft=true);if(e.key==='ArrowRight')ship&&(ship.tRight=true);});
document.addEventListener('keyup',e=>{if(e.key==='ArrowLeft')ship&&(ship.tLeft=false);if(e.key==='ArrowRight')ship&&(ship.tRight=false);});
canvas.addEventListener('mousemove',e=>{if(ship&&gameActive)ship.x=Math.max(28,Math.min(W-28,e.clientX));});
canvas.addEventListener('touchmove',e=>{e.preventDefault();if(ship&&gameActive)ship.x=Math.max(28,Math.min(W-28,e.touches[0].clientX));},{passive:false});

async function endGame(reason){
  if(!gameActive)return;gameActive=false;
  const timeTaken=Math.round((Date.now()-sessionStart)/1000),acc=totalShots>0?Math.round(correctShots/totalShots*100):0,stars=acc>=85?3:acc>=60?2:acc>=35?1:0;
  try{await fetch('/api/session/end',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,score,difficulty:currentMode,level:wave,time_taken:timeTaken,total_attempts:totalShots,correct_attempts:correctShots,combo_max:bestStreak,operators_used:operatorCounts})});}catch(e){}
  document.getElementById('rEmoji').textContent=reason==='dead'?'💀':'🚀';
  document.getElementById('rTitle').textContent=reason==='dead'?'Oh no!':'Level Done!';
  document.getElementById('rTitle').style.color=reason==='dead'?'#ff6b35':'#00e676';
  document.getElementById('rSub').textContent=reason==='dead'?'The aliens got through! Try again!':'You blasted all the aliens! Great job!';
  document.getElementById('rStars').textContent=['','⭐','⭐⭐','⭐⭐⭐'][stars]||'⭐';
  document.getElementById('rScore').textContent=score.toLocaleString();document.getElementById('rWave').textContent=wave;document.getElementById('rAcc').textContent=acc+'%';document.getElementById('rStreak').textContent=bestStreak;
  document.getElementById('resultOverlay').classList.add('show');
}
function restartGame(){document.getElementById('resultOverlay').classList.remove('show');score=0;wave=1;lives=cfg.lives||3;streak=0;bestStreak=0;totalShots=0;correctShots=0;waveKills=0;waveTarget=6;operatorCounts={};enemies=[];bullets=[];particles=[];explosions=[];currentEq=null;frameCount=0;betweenWaves=false;initShip();updateHUD();renderLives();gameActive=true;sessionStart=Date.now();announceWave('Wave 1! 🚀');}
async function logAction(d){if(!sessionId)return;try{await fetch('/api/log/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,level:wave,difficulty:currentMode,...d})});}catch(e){}}

function randInt(a,b){return Math.floor(Math.random()*(b-a+1))+a;}
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}

const sty=document.createElement('style');sty.textContent=`@keyframes scorePop{0%{opacity:1;transform:translateX(-50%) translateY(0)}100%{opacity:0;transform:translateX(-50%) translateY(-60px)}}`;document.head.appendChild(sty);
if(!ctx.roundRect)ctx.roundRect=function(x,y,w,h,r){this.beginPath();this.moveTo(x+r,y);this.arcTo(x+w,y,x+w,y+h,r);this.arcTo(x+w,y+h,x,y+h,r);this.arcTo(x,y+h,x,y,r);this.arcTo(x,y,x+w,y,r);this.closePath();};

async function init(){
  createAdaptiveHUD('adaptHUDContainer');gradeConfig=await ai.loadGradeConfig();await ai.loadProfile();const s=ai.getFixedSettings(currentMode);applySettings(s);
  try{const r=await fetch('/api/session/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game_type:'blaster',difficulty:currentMode,level:1})});const d=await r.json();sessionId=d.session_id;}catch(e){}
  initShip();initStars();renderLives();updateHUD();gameActive=true;sessionStart=Date.now();announceWave('Wave 1! 🚀');gameLoop();
}
window.addEventListener('load',init);
