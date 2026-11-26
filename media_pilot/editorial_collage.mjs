import {copyFileSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const colors = {
  tarih: {paper: '#e9dbb8', ink: '#302a20', accent: '#803b32', label: 'ARŞİV DÜZENİ'},
  bakim: {paper: '#f1dfdc', ink: '#302536', accent: '#8d4265', label: 'ETİKET REHBERİ'},
};
const escape = value => value.replace(/[&<>"']/g, char =>
  ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'})[char]);

export function collageHTML({brand, title, credit = '', seconds, photo = false}) {
  if (!Object.hasOwn(colors, brand) || typeof title !== 'string' || !title.trim() || title.length > 170 ||
      typeof credit !== 'string' || credit.length > 260 || (photo && !credit.trim()) ||
      typeof photo !== 'boolean' || !Number.isFinite(seconds) || seconds < 3 || seconds > 9) {
    throw new Error('Invalid editorial collage options');
  }
  const {paper, ink, accent, label} = colors[brand];
  return `<!doctype html><html lang="tr"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="connect-src 'none'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; script-src 'self' 'unsafe-inline'">
<style>
  *{box-sizing:border-box}body{margin:0;background:${paper};color:${ink}}
  #paper-board{position:relative;width:1080px;height:1920px;overflow:hidden;background:
    radial-gradient(circle at 2px 2px,#302a2013 1px,transparent 2px) 0 0/13px 13px,${paper}}
  .sheet{position:absolute;border:2px solid ${ink};background:#fff7e2;box-shadow:12px 19px #302a2026}
  #note{left:45px;right:232px;top:286px;height:680px;background:repeating-linear-gradient(
    0deg,#fff7e2 0 27px,#8d786b3b 28px,#fff7e2 31px)}
  #plate{left:230px;right:82px;top:470px;height:730px;border:22px solid #fcf0d7;overflow:hidden}
  #plate img{width:100%;height:100%;object-fit:contain;background:${ink}}
  #plate-pattern{height:100%;background:repeating-linear-gradient(128deg,#302a2024 0 3px,transparent 4px 15px),
    radial-gradient(circle at 65% 35%,${accent} 0 19%,transparent 19.5% 27%,${accent} 27.5% 29%,${paper} 29.5%);}
  #strip{position:absolute;left:115px;right:115px;top:1150px;padding:34px 40px;background:${ink};color:#fff6e9;
    clip-path:polygon(0 2%,97% 0,100% 96%,4% 100%);border-top:8px solid ${accent}}
  #strip small,footer{font:700 25px sans-serif;letter-spacing:1.2px}
  h1{font:bold 68px Georgia,serif;line-height:1.07;margin:.3em 0 .1em;overflow-wrap:anywhere}
  footer{position:absolute;left:82px;right:82px;top:160px;line-height:1.3}
</style>
<div id="paper-board" data-composition-id="paper-board" data-width="1080" data-height="1920" data-start="0" data-duration="${seconds}">
  <footer>TEMSİLÎ EDİTORYAL KOLAJ${credit ? '<br>'+escape(credit) : ''}</footer>
  <div class="sheet" id="note"></div>
  <div class="sheet" id="plate">${photo ? '<img src="photo.jpg" alt="">' : '<div id="plate-pattern"></div>'}</div>
  <div id="strip"><small>${label}</small><h1>${escape(title)}</h1></div>
</div>
<script src="gsap.min.js"></script>
<script>
window.__timelines = window.__timelines || {};
const timeline = gsap.timeline({paused:true});
timeline.fromTo('#note',{x:-88,y:34,rotation:-10},{x:0,y:0,rotation:-6,duration:.55,ease:'power2.out'},0)
 .fromTo('#plate',{x:120,y:84,rotation:10,opacity:0},{x:0,y:0,rotation:4,opacity:1,duration:.76,ease:'power3.out'},.16)
 .fromTo('#strip',{y:120,opacity:0},{y:0,opacity:1,duration:.55,ease:'power2.out'},.46)
 .to('#plate',{rotation:2,y:-18,duration:${seconds}-.92,ease:'sine.inOut'},.92);
window.__timelines['paper-board'] = timeline;
</script></html>`;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const directory = resolve(process.argv[2]);
  const options = JSON.parse(readFileSync(join(directory, 'collage.json'), 'utf8'));
  writeFileSync(join(directory, 'index.html'), collageHTML(options));
  copyFileSync(join(here, 'node_modules/gsap/dist/gsap.min.js'), join(directory, 'gsap.min.js'));
}
