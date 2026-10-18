/* Offline WebGL orbit viewer. No framework, imports, CDN, or network calls.
 * Positions use one Earth–Moon separation as unit. z is ALWAYS spin north.
 * The browser interpolates exported samples; it never solves the orbit.
 */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const data = window.ORBIT_DATA;
  const canvas = $('space');
  if (!data) { $('webgl-error').hidden = false; return; }
  const gl = canvas.getContext('webgl', {antialias: true, alpha: true});
  if (!gl) { $('webgl-error').hidden = false; return; }
  const I = data.inputs, V = data.verification, rows = data.samples;
  const T = V.period_normalized, L = I.separation_km, mu = I.mu;
  const Rearth = I.primary_solid_radius_km / L;
  const Rmoon = I.secondary_radius_km / L;
  const colors = {out: [.47,.89,.87,1], in: [1,.78,.49,1], earth: [.15,.34,.48,1], moon: [.53,.60,.64,1],
    white: [.95,.98,1,1], grid: [.25,.39,.48,.25], axis: [.28,.48,.57,.5]};
  const add = (a,b) => a.map((v,j)=>v+b[j]);
  const sub = (a,b) => a.map((v,j)=>v-b[j]);
  const mul = (a,s) => a.map(v=>v*s);
  const dot = (a,b) => a.reduce((s,v,j)=>s+v*b[j],0);
  const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm = a => Math.hypot(...a);
  const unit = a => mul(a,1/(norm(a)||1));
  const clamp = (x,a,b) => Math.max(a,Math.min(b,x));
  const rz = (p,t) => [Math.cos(t)*p[0]-Math.sin(t)*p[1],Math.sin(t)*p[0]+Math.cos(t)*p[1],p[2]];
  const identity = () => new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
  function mm(a,b) {
    const c = new Float32Array(16);
    for(let j=0;j<4;j++) for(let k=0;k<4;k++) for(let i=0;i<4;i++) c[j*4+i]+=a[k*4+i]*b[j*4+k];
    return c;
  }
  function model(center,scale=1,angle=0) {
    const c=Math.cos(angle)*scale,s=Math.sin(angle)*scale;
    return new Float32Array([c,s,0,0, -s,c,0,0, 0,0,scale,0, ...center,1]);
  }
  function lookAt(eye,target) {
    const z=unit(sub(eye,target));
    const x=unit(cross(Math.abs(z[2])>.9999?[0,1,0]:[0,0,1],z));
    const y=cross(z,x);
    return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
  }
  function perspective(aspect,near,far) {
    const f=1/Math.tan(Math.PI/8),nf=1/(near-far);
    return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]);
  }
  function shader(type,source) {
    const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s));
    return s;
  }
  const program=gl.createProgram();
  gl.attachShader(program,shader(gl.VERTEX_SHADER,`
    attribute vec3 position; attribute vec3 normal;
    uniform mat4 mvp; uniform mat4 model; uniform float pointSize;
    varying vec3 n;
    void main(){gl_Position=mvp*vec4(position,1.);gl_PointSize=pointSize;n=mat3(model)*normal;}
  `));
  gl.attachShader(program,shader(gl.FRAGMENT_SHADER,`
    precision mediump float;
    uniform vec4 color; uniform bool lit; uniform bool point;
    varying vec3 n;
    void main(){
      if(point && distance(gl_PointCoord,vec2(.5))>.5) discard;
      float light=lit ? .43+.57*max(0.,dot(normalize(n),normalize(vec3(-.4,-.6,1.)))) : 1.;
      gl_FragColor=vec4(color.rgb*light,color.a);
    }
  `));
  gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  const attr={p:gl.getAttribLocation(program,'position'),n:gl.getAttribLocation(program,'normal')};
  const uniforms={};for(const name of ['mvp','model','pointSize','color','lit','point']) uniforms[name]=gl.getUniformLocation(program,name);
  gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  gl.clearColor(0,0,0,0);

  function mesh(points,normals=null) {
    const p=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,p);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(points.flat()),gl.STATIC_DRAW);
    let n=null;
    if(normals){n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,n);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(normals.flat()),gl.STATIC_DRAW);}
    return {p,n,count:points.length};
  }
  function destroy(m){if(m){gl.deleteBuffer(m.p);if(m.n)gl.deleteBuffer(m.n);}}
  const spherePoints=[];
  const sp=(lat,lon)=>[Math.cos(lat)*Math.cos(lon),Math.cos(lat)*Math.sin(lon),Math.sin(lat)];
  for(let j=0;j<30;j++)for(let k=0;k<60;k++){
    const a=-Math.PI/2+j*Math.PI/30,b=a+Math.PI/30,c=k*2*Math.PI/60,d=c+2*Math.PI/60;
    spherePoints.push(sp(a,c),sp(b,c),sp(b,d),sp(a,c),sp(b,d),sp(a,d));
  }
  const sphere=mesh(spherePoints,spherePoints);
  const wirePoints=[];
  function wireCurve(points){for(let j=1;j<points.length;j++)wirePoints.push(points[j-1],points[j]);}
  for(let j=-2;j<=2;j++)wireCurve(Array.from({length:121},(_,k)=>sp(j*Math.PI/6,k*2*Math.PI/120)));
  for(let j=0;j<12;j++)wireCurve(Array.from({length:61},(_,k)=>sp(-Math.PI/2+k*Math.PI/60,j*2*Math.PI/12)));
  const wire=mesh(wirePoints);
  const gridPoints=[];
  for(let j=-4;j<=4;j++){const a=j*.5;gridPoints.push([-2,a,0],[2,a,0],[a,-2,0],[a,2,0]);}
  const grid=mesh(gridPoints);
  const axesMesh=mesh([[-2,0,0],[2,0,0],[0,-2,0],[0,2,0],[0,0,-.45],[0,0,.45]]);
  const circle=mesh(Array.from({length:361},(_,j)=>[Math.cos(j*Math.PI/180),Math.sin(j*Math.PI/180),0]));
  const dotMesh=mesh([[0,0,0]]);

  let frame='rotating', time=0, playing=false, bankPhase='before', last=0;
  let target=[0,0,0], radius=6, yaw=-1.15,pitch=.63;
  let mode='orbit',flyPos=[0,0,0],flyYaw=0,flyPitch=0;
  let vp=identity(), eye=[0,0,0],camForward=[0,0,-1];
  let pathOut,pathIn,fitPoints=[],needsDraw=true,dragging=null;
  const keys=new Set();
  function positionInFrame(q,t){return frame==='rotating'?q:rz(frame==='barycentric'?sub(q,[mu,0,0]):q,t);}
  function earthPosition(t){return frame==='barycentric'?rz([-mu,0,0],t):[0,0,0];}
  function moonPosition(t){return frame==='rotating'?[1,0,0]:rz([frame==='barycentric'?1-mu:1,0,0],t);}
  function directionInFrame(d,t){return frame==='rotating'?d:rz(d,t);}
  function rebuildPath(){
    destroy(pathOut);destroy(pathIn);
    const out=[],incoming=[];
    rows.forEach(row=>{const p=positionInFrame(row.slice(1,4),row[0]);(row[0]<=data.apogee_time?out:incoming).push(p);});
    if(out.length)incoming.unshift(out[out.length-1]);
    pathOut=mesh(out);pathIn=mesh(incoming);
    fitPoints=out.concat(incoming);
    // Include the lunar reference circle as well as the trajectory, so the
    // Moon is never lost outside the initial overview's field of view.
    for(let j=0;j<72;j++){const a=j*2*Math.PI/72,r=frame==='barycentric'?1-mu:1;fitPoints.push([r*Math.cos(a),r*Math.sin(a),0]);}
    needsDraw=true;
  }
  function fitCamera(){
    const low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity];
    fitPoints.forEach(p=>p.forEach((v,j)=>{low[j]=Math.min(low[j],v);high[j]=Math.max(high[j],v);}));
    target=low.map((v,j)=>(v+high[j])/2);
    const direction=[Math.cos(pitch)*Math.cos(yaw),Math.cos(pitch)*Math.sin(yaw),Math.sin(pitch)];
    const right=unit(cross(Math.abs(direction[2])>.9999?[0,1,0]:[0,0,1],direction)),up=cross(direction,right);
    const aspect=canvas.clientWidth/canvas.clientHeight,tan=Math.tan(Math.PI/8);
    radius=1;
    for(const p of fitPoints){const offset=sub(p,target);radius=Math.max(radius,dot(offset,direction)+1.24*Math.max(Math.abs(dot(offset,right))/(tan*aspect),Math.abs(dot(offset,up))/tan));}
  }
  // Cubic Hermite position interpolation uses stored dq/dt in this frame.
  // This avoids the straight-chord Earth intersections of sparse samples.
  function stateAt(t){
    if(t>=T-1e-12)return (bankPhase==='after'?V.post_bank_state:V.pre_bank_state).slice();
    if(t<=0)return V.initial_state.slice();
    let lo=0,hi=rows.length-1;
    while(hi-lo>1){const mid=(hi+lo)>>1;if(rows[mid][0]<=t)lo=mid;else hi=mid;}
    const a=rows[lo],b=rows[hi],dt=b[0]-a[0],u=(t-a[0])/dt,u2=u*u,u3=u2*u;
    const h00=2*u3-3*u2+1,h10=u3-2*u2+u,h01=-2*u3+3*u2,h11=u3-u2;
    const d00=(6*u2-6*u)/dt,d10=3*u2-4*u+1,d01=(-6*u2+6*u)/dt,d11=3*u2-2*u;
    return [0,1,2].map(j=>h00*a[1+j]+h10*dt*a[4+j]+h01*b[1+j]+h11*dt*b[4+j])
      .concat([0,1,2].map(j=>d00*a[1+j]+d10*a[4+j]+d01*b[1+j]+d11*b[4+j]));
  }
  function camera(){
    if(mode==='orbit'){
      eye=add(target,[radius*Math.cos(pitch)*Math.cos(yaw),radius*Math.cos(pitch)*Math.sin(yaw),radius*Math.sin(pitch)]);
      camForward=unit(sub(target,eye));
    }else{
      eye=flyPos.slice();camForward=[Math.cos(flyPitch)*Math.cos(flyYaw),Math.cos(flyPitch)*Math.sin(flyYaw),Math.sin(flyPitch)];
    }
    const near=clamp((mode==='orbit'?radius:norm(sub(eye,earthPosition(time))))*.0001,1e-7,.001);
    vp=mm(perspective(canvas.width/canvas.height,near,100),lookAt(eye,add(eye,camForward)));
  }
  function draw(m,primitive,color,transform=identity(),lit=false,pointSize=7){
    gl.bindBuffer(gl.ARRAY_BUFFER,m.p);gl.enableVertexAttribArray(attr.p);gl.vertexAttribPointer(attr.p,3,gl.FLOAT,false,0,0);
    if(m.n){gl.bindBuffer(gl.ARRAY_BUFFER,m.n);gl.enableVertexAttribArray(attr.n);gl.vertexAttribPointer(attr.n,3,gl.FLOAT,false,0,0);}
    else{gl.disableVertexAttribArray(attr.n);gl.vertexAttrib3f(attr.n,0,0,1);}
    gl.uniformMatrix4fv(uniforms.mvp,false,mm(vp,transform));gl.uniformMatrix4fv(uniforms.model,false,transform);
    gl.uniform4fv(uniforms.color,color);gl.uniform1i(uniforms.lit,lit);gl.uniform1i(uniforms.point,primitive===gl.POINTS);gl.uniform1f(uniforms.pointSize,pointSize);
    gl.drawArrays(primitive,0,m.count);
  }
  let vectorMesh=null;
  function drawVectors(){
    if(!$('vectors').checked)return;
    const pre=V.pre_bank_state,post=V.post_bank_state,q=pre.slice(0,3),base=positionInFrame(q,T);
    const vin=add(pre.slice(3),cross([0,0,1],q)),vout=add(post.slice(3),cross([0,0,1],q)),dv=sub(post.slice(3),pre.slice(3));
    [vin,vout,mul(dv,20)].forEach((v,j)=>{
      const d=mul(directionInFrame(v,T),.0016);
      const end=add(base,d),side=mul(unit(cross(d,unit(base))),norm(d)*.05);
      const back=sub(end,mul(d,.16));
      const points=[base,end,end,add(back,side),end,sub(back,side)];
      destroy(vectorMesh);vectorMesh=mesh(points);draw(vectorMesh,gl.LINES,[colors.white,colors.out,colors.in][j]);
    });
  }
  function label(id,p,offset){
    const v=[...p,1],clip=[0,1,2,3].map(i=>vp[i]*v[0]+vp[4+i]*v[1]+vp[8+i]*v[2]+vp[12+i]);
    const el=$(id),x=clip[0]/clip[3],y=clip[1]/clip[3];
    el.hidden=clip[3]<=0||Math.abs(x)>1||Math.abs(y)>1;
    el.style.left=((x+1)*canvas.clientWidth/2+offset)+'px';el.style.top=((1-y)*canvas.clientHeight/2+8)+'px';
  }
  function updateReadout(state){
    const q=state.slice(0,3),w=add(state.slice(3),cross([0,0,1],q)),h=cross(q,w);
    $('day').value=(time*V.units.time_s/86400).toFixed(4)+' d';
    $('altitude').textContent=Math.max(0,norm(q)*L-I.primary_solid_radius_km).toLocaleString('en-US',{maximumFractionDigits:0})+' km';
    $('speed').textContent=(norm(w)*V.units.velocity_m_s/1000).toFixed(3)+' km/s';
    $('inclination').textContent=(Math.acos(clamp(h[2]/norm(h),-1,1))*180/Math.PI).toFixed(3)+'°';
    $('event-label').textContent=time===0?'Departure · after bank':time>=T-1e-12?(bankPhase==='before'?'Return · before bank':'Return · after bank'):Math.abs(time-data.apogee_time)<.00001?'Apogee':time<data.apogee_time?'Outbound coast':'Inbound coast';
    $('timeline').value=time/T;
    $('incoming').setAttribute('aria-pressed',String(time===T&&bankPhase==='before'));
    $('outgoing').setAttribute('aria-pressed',String(time===T&&bankPhase==='after'));
  }
  function render(){
    const dpr=Math.min(window.devicePixelRatio||1,2),width=Math.round(canvas.clientWidth*dpr),height=Math.round(canvas.clientHeight*dpr);
    if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    gl.viewport(0,0,width,height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);camera();
    const earth=earthPosition(time),moon=moonPosition(time);
    if($('grid').checked){gl.depthMask(false);draw(grid,gl.LINES,colors.grid,model(earth));draw(axesMesh,gl.LINES,colors.axis,model(earth));gl.depthMask(true);}
    draw(circle,gl.LINE_STRIP,[.38,.49,.56,.6],model(frame==='barycentric'?[0,0,0]:earth,frame==='barycentric'?1-mu:1));
    draw(pathOut,gl.LINE_STRIP,colors.out);draw(pathIn,gl.LINE_STRIP,colors.in);
    draw(sphere,gl.TRIANGLES,colors.earth,model(earth,Rearth),true);
    const spin=I.lunar_sidereal_period_days/I.primary_sidereal_day_days-(frame==='rotating'?1:0);
    draw(wire,gl.LINES,[.35,.58,.70,.62],model(earth,Rearth*1.001,spin*time));
    // Thin, true-radius 100-km interface, visible in Earth close-up.
    draw(wire,gl.LINES,[.35,.70,.72,.17],model(earth,(I.primary_solid_radius_km+100)/L));
    draw(sphere,gl.TRIANGLES,colors.moon,model(moon,Rmoon),true);
    draw(dotMesh,gl.POINTS,[.67,.75,.79,1],model(moon),false,5*dpr);
    const state=stateAt(time),craft=positionInFrame(state.slice(0,3),time);
    draw(dotMesh,gl.POINTS,colors.white,model(craft),false,7*dpr);
    drawVectors();
    label('earth-label',earth,9);label('moon-label',moon,9);updateReadout(state);
    needsDraw=false;
  }
  function setMode(next){
    camera();
    if(next===mode)return;
    if(next==='fly'){flyPos=eye.slice();flyYaw=Math.atan2(camForward[1],camForward[0]);flyPitch=Math.asin(camForward[2]);}
    else{radius=clamp(norm(sub(eye,target)),.0002,20);const d=unit(sub(eye,target));yaw=Math.atan2(d[1],d[0]);pitch=Math.asin(d[2]);}
    mode=next;keys.clear();
    $('orbit-mode').setAttribute('aria-pressed',String(mode==='orbit'));$('fly-mode').setAttribute('aria-pressed',String(mode==='fly'));
    $('camera-help').textContent=mode==='orbit'?'Drag to orbit · wheel to zoom · right-drag or Shift-drag to pan.':'Click the scene; drag to look. W/S forward/back · A/D strafe · Q/E down/up · Shift faster. Wheel moves forward/back.';
    needsDraw=true;
  }
  function pause(){playing=false;$('play').textContent='▶ Play coast';}
  function jump(t,phase='before'){time=clamp(t,0,T);bankPhase=phase;pause();needsDraw=true;}
  function preset(name){
    setMode('orbit');yaw=-1.15;pitch=.63;
    if(name==='top'){pitch=Math.PI/2-.001;yaw=-Math.PI/2;}
    if(name==='side'){pitch=0;yaw=-Math.PI/2;}
    if(name==='polar'){
      const initial=V.initial_state,h=unit(cross(initial.slice(0,3),add(initial.slice(3),cross([0,0,1],initial.slice(0,3)))));
      yaw=Math.atan2(h[1],h[0]);pitch=Math.asin(h[2]);
    }
    fitCamera();
    if(name==='earth'){
      jump(T);target=earthPosition(T);radius=.085;yaw=-.8;pitch=.3;
      $('vectors').checked=true;$('vector-note').hidden=false;
      $('fly-speed').value='0.001';
    }
    needsDraw=true;
  }
  $('frame').addEventListener('change',()=>{
    frame=$('frame').value;rebuildPath();preset('overview');
    const descriptions={rotating:['LUNAR-CO-MOVING','Earth is at the origin; the Moon is fixed on +x. The trajectory closes in this frame after the bank.'],earth:['EARTH-CENTERED · NON-ROTATING','Axes do not rotate; the Moon moves. The translating Earth-centered origin is not a globally inertial frame. The endpoint is rotated 1.577° relative to departure.'],barycentric:['BARYCENTRIC INERTIAL','The Earth–Moon barycenter is fixed; Earth and Moon both move. These are inertial axes in the circular model. The endpoint need not coincide with departure.']};
    $('frame-label').textContent=descriptions[frame][0];$('frame-explanation').textContent=descriptions[frame][1];
  });
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>preset(button.dataset.view)));
  $('timeline').addEventListener('input',()=>jump(Number($('timeline').value)*T));
  $('play').addEventListener('click',()=>{playing=!playing;if(playing&&time>=T)time=0;$('play').textContent=playing?'❚❚ Pause':'▶ Play coast';needsDraw=true;});
  $('apogee').addEventListener('click',()=>jump(data.apogee_time));
  $('incoming').addEventListener('click',()=>jump(T,'before'));$('outgoing').addEventListener('click',()=>jump(T,'after'));
  $('orbit-mode').addEventListener('click',()=>setMode('orbit'));$('fly-mode').addEventListener('click',()=>setMode('fly'));
  $('focus').addEventListener('click',()=>{setMode('orbit');target=positionInFrame(stateAt(time).slice(0,3),time);radius=.04;needsDraw=true;});
  ['grid','vectors'].forEach(id=>$(id).addEventListener('change',()=>{needsDraw=true;$('vector-note').hidden=!$('vectors').checked;}));
  canvas.addEventListener('contextmenu',event=>event.preventDefault());
  canvas.addEventListener('pointerdown',event=>{canvas.focus();canvas.setPointerCapture(event.pointerId);dragging={x:event.clientX,y:event.clientY,pan:event.button===2||event.shiftKey};});
  canvas.addEventListener('pointermove',event=>{
    if(!dragging)return;
    const dx=event.clientX-dragging.x,dy=event.clientY-dragging.y;dragging.x=event.clientX;dragging.y=event.clientY;
    if(mode==='fly'){flyYaw-=dx*.005;flyPitch=clamp(flyPitch-dy*.005,-1.56,1.56);}
    else if(dragging.pan){
      camera();const right=unit(cross(camForward,[0,0,1])),up=cross(right,camForward),scale=radius*.0015;
      target=add(target,add(mul(right,-dx*scale),mul(up,dy*scale)));
    }else{yaw-=dx*.006;pitch=clamp(pitch+dy*.006,-1.569,1.569);}
    needsDraw=true;
  });
  function endDrag(){dragging=null;}
  canvas.addEventListener('pointerup',endDrag);canvas.addEventListener('pointercancel',endDrag);canvas.addEventListener('lostpointercapture',endDrag);
  canvas.addEventListener('wheel',event=>{
    event.preventDefault();
    if(mode==='orbit')radius=clamp(radius*Math.exp(clamp(event.deltaY,-120,120)*.002),.00003,30);
    else{camera();flyPos=add(flyPos,mul(camForward,-Math.sign(event.deltaY)*Number($('fly-speed').value)*.2));}
    needsDraw=true;
  },{passive:false});
  canvas.addEventListener('keydown',event=>{
    if(['w','a','s','d','q','e','shift'].includes(event.key.toLowerCase())){keys.add(event.key.toLowerCase());event.preventDefault();}
    if(event.key==='Escape'){keys.clear();endDrag();}
  });
  window.addEventListener('keyup',event=>keys.delete(event.key.toLowerCase()));
  window.addEventListener('blur',()=>keys.clear());canvas.addEventListener('blur',()=>keys.clear());
  new ResizeObserver(()=>{needsDraw=true;}).observe(canvas);
  document.addEventListener('visibilitychange',()=>{last=0;keys.clear();});
  function tick(now){
    const dt=last?Math.min((now-last)/1000,.08):0;last=now;
    if(playing){time=Math.min(T,time+dt*T/Number($('rate').value));bankPhase='before';needsDraw=true;if(time>=T)pause();}
    if(mode==='fly'&&keys.size){
      camera();const right=unit(cross(camForward,[0,0,1]));let motion=[0,0,0];
      if(keys.has('w'))motion=add(motion,camForward);if(keys.has('s'))motion=sub(motion,camForward);
      if(keys.has('d'))motion=add(motion,right);if(keys.has('a'))motion=sub(motion,right);
      if(keys.has('e'))motion=add(motion,[0,0,1]);if(keys.has('q'))motion=sub(motion,[0,0,1]);
      flyPos=add(flyPos,mul(motion,dt*Number($('fly-speed').value)*(keys.has('shift')?5:1)));needsDraw=true;
    }
    if(needsDraw)render();requestAnimationFrame(tick);
  }
  rebuildPath();fitCamera();requestAnimationFrame(tick);
  // Read-only diagnostics for reproducible browser checks, not a second model.
  window.orbitViewer={get state(){return {frame,time,mode,eye:eye.slice(),target:target.slice(),playing,bankPhase};},stateAt,
    get webglError(){return gl.getError();}};
})();
