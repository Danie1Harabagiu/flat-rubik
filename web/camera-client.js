/* Local-only camera capture. No images leave the browser. */
(() => {
  const order = 'FRBLUD', names = {F:'rosu',R:'verde',B:'portocaliu',L:'albastru',U:'galben',D:'alb'};
  const top = {F:'galben',R:'galben',B:'galben',L:'galben',U:'portocaliu',D:'rosu'};
  const palette = {rosu:'#e33333',verde:'#18ae50',portocaliu:'#ff9200',albastru:'#298de0',galben:'#ffe000',alb:'#ffffff'};
  let root, video, stream, samples, grids, events=[], generation=0, observer;
  const stop = () => { if(observer)observer.disconnect(); observer=null; if(stream) stream.getTracks().forEach(t=>t.stop()); stream=null; };
  const button = (label, action, parent=root) => {const b=document.createElement('button'); b.textContent=label; b.onclick=action; b.style.cssText='padding:12px;margin:5px;border-radius:8px;border:1px solid #87639d;background:white;color:#291b34;cursor:pointer'; parent.append(b); return b;};
  const message = text => {root.querySelector('[data-message]').textContent=text;};
  function shell() {
    root.replaceChildren(); const title=document.createElement('h2');title.textContent='Scanare cub 3×3';root.append(title);
    const m=document.createElement('p');m.dataset.message='';m.setAttribute('role','status');root.append(m);
  }
  // sRGB -> CIE Lab, calibrated against the six physical centers.
  function lab(rgb) {
    const [r,g,b]=rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});
    const f=v=>v>216/24389?Math.cbrt(v):(24389/27*v+16)/116;
    const x=f((.4124564*r+.3575761*g+.1804375*b)/.95047), y=f(.2126729*r+.7151522*g+.072175*b), z=f((.0193339*r+.119192*g+.9503041*b)/1.08883);
    return [116*y-16,500*(x-y),200*(y-z)];
  }
  const distance=(a,b)=>a.reduce((s,v,i)=>s+(v-b[i])**2,0);
  function recognize() {
    const centers=Object.fromEntries([...order].map(f=>[f,lab(samples[f][4])]));
    if([...order].some((f,i)=>[...order].slice(i+1).some(g=>distance(centers[f],centers[g])<64))) {
      shell();message('Doua centre sunt prea asemanatoare. Verifica lumina si orientarea, apoi rescaneaza.');
      button('Rescaneaza',start);button('Renunta',cancel);return;
    }
    grids=Object.fromEntries([...order].map(f=>[f,samples[f].map((rgb,i)=>names[i===4?f:[...order].reduce((best,g)=>distance(lab(rgb),centers[g])<distance(lab(rgb),centers[best])?g:best,'F')])]));
    review();
  }
  function review(error='') {
    stop();shell();message(error || 'Verifica toate cele 54 de culori. Clic pe o casuta schimba culoarea; centrele raman fixe.');
    const cards=document.createElement('div');cards.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:16px;max-width:640px;margin:auto';root.append(cards);
    for(const f of order) {
      const card=document.createElement('div');card.textContent=`${f}: ${names[f]} · sus ${top[f]}`;cards.append(card);
      const grid=document.createElement('div');grid.style.cssText='display:grid;grid-template-columns:repeat(3,44px);margin:8px auto;width:132px';card.append(grid);
      grids[f].forEach((color,i)=>{const b=button('',()=>{const colors=Object.values(names);grids[f][i]=colors[(colors.indexOf(grids[f][i])+1)%6];b.style.background=palette[grids[f][i]];b.title=grids[f][i];b.setAttribute('aria-label',`${f} ${i+1}: ${grids[f][i]}`);},grid);b.style.cssText=`width:40px;height:40px;padding:0;margin:2px;border:2px solid #392642;border-radius:4px;background:${palette[color]}`;b.title=color;b.setAttribute('aria-label',`${f} ${i+1}: ${color}`);b.disabled=i===4;});
    }
    button('Aplica configuratia',()=>{events.push({type:'submit',grids});message('Verific configuratia...');});
    button('Rescaneaza',start);button('Renunta',cancel);
  }
  function capture() {
    if(!video.videoWidth) {message('Asteapta imaginea camerei.');return;}
    const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
    const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(video,0,0);
    const side=Math.min(canvas.width,canvas.height)*.72, left=(canvas.width-side)/2, upper=(canvas.height-side)/2, patch=Math.max(2,Math.floor(side/18));
    const face=order[Object.keys(samples).length];samples[face]=Array.from({length:9},(_,i)=>{
      const pixels=ctx.getImageData(Math.round(left+(i%3+.5)*side/3-patch/2),Math.round(upper+(Math.floor(i/3)+.5)*side/3-patch/2),patch,patch).data;
      return [0,1,2].map(c=>{const channel=[];for(let k=c;k<pixels.length;k+=4)channel.push(pixels[k]);channel.sort((a,b)=>a-b);return channel[Math.floor(channel.length/2)];});
    });
    if(Object.keys(samples).length===6)recognize();else guide();
  }
  function guide() {const f=order[Object.keys(samples).length];message(`${Object.keys(samples).length+1}/6: centrul ${names[f]} spre camera, culoarea ${top[f]} SUS. Aliniaza cele 9 patrate in grila. Nu roti straturile intre capturi.`);}
  async function start() {
    const token=++generation;stop();samples={};shell();message('Cer permisiunea pentru camera...');button('Renunta',cancel);
    try {
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('Camera necesita HTTPS sau localhost si un browser compatibil.');
      const acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
      if(token!==generation){acquired.getTracks().forEach(t=>t.stop());return;}
      stream=acquired;shell();const stage=document.createElement('div');stage.style.cssText='position:relative;width:min(100%,540px);margin:auto';root.append(stage);
      video=document.createElement('video');video.muted=true;video.playsInline=true;video.style.cssText='display:block;width:100%';video.srcObject=stream;stage.append(video);await video.play();
      if(token!==generation)return;
      const overlay=document.createElement('div');overlay.style.cssText='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);display:grid;grid-template-columns:repeat(3,1fr);pointer-events:none';stage.append(overlay);
      const resize=()=>{const side=Math.min(video.clientWidth,video.clientHeight)*.72;overlay.style.width=side+'px';overlay.style.height=side+'px';};
      for(let i=0;i<9;i++){const cell=document.createElement('div');cell.style.cssText='border:1px solid white;box-shadow:inset 0 0 0 1px #2228';overlay.append(cell);}
      video.onresize=resize;observer=new ResizeObserver(resize);observer.observe(video);resize();
      button('Captureaza fata',capture);button('Renunta',cancel);guide();
    } catch(e) {if(token!==generation)return;stop();shell();message('Camera nu a pornit: '+e.message);button('Reincearca',start);button('Renunta',cancel);}
  }
  function cancel(){generation++;stop();if(root)root.remove();root=null;events.push({type:'cancel'});}
  window.flatRubikCamera={
    open(){if(root)cancel();events=[];root=document.createElement('section');root.setAttribute('role','dialog');root.setAttribute('aria-label','Scanare camera');root.style.cssText='position:fixed;inset:0;z-index:2147483647;overflow:auto;box-sizing:border-box;padding:16px;background:#efe5f7;color:#291b34;font:16px sans-serif;text-align:center';document.body.append(root);shell();message('Scaneaza cele sase fete. Pozele raman local. Lumina uniforma, fara reflexii. Porneste camera doar cand esti pregatit.');button('Porneste camera',start);button('Renunta',cancel);},
    pollJson(){return JSON.stringify(events.shift()||null);},
    error(text){review(text);},
    finish(){generation++;stop();if(root)root.remove();root=null;},
    cancel
  };
  window.addEventListener('pagehide',()=>{generation++;stop();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&stream){generation++;stop();shell();message('Camera oprita cat timp fila este ascunsa.');button('Reia scanarea',start);button('Renunta',cancel);}});
})();
