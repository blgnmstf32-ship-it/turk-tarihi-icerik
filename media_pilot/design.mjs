import {moisture} from './moisture.mjs';
import {copyFileSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const WIDTH = 720;
export const HEIGHT = 1280;
export const FPS = 30;
const here = dirname(fileURLToPath(import.meta.url));
const escape = (value) => value.replace(/[&<>"']/g, (char) => (
  {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[char]);

const motionPresets = JSON.parse(readFileSync(join(here, 'motion_presets.json'), 'utf8'));

export function prepare(directory, brand, effect = '') {
  if (effect && !Object.hasOwn(motionPresets, effect)) throw new Error('Unsupported motion effect');
  const preset = motionPresets[effect];
  const profiles = JSON.parse(readFileSync(join(here, 'profiles.json'), 'utf8'));
  const scene = profiles[brand];
  if (!scene) throw new Error('Unknown brand');
  const seconds = scene.seconds;
  mkdirSync(directory, {recursive: true});
  const content = `<!doctype html><html lang="tr"><head><meta charset="utf-8">
  <style>
    @font-face{font-family:PilotSans;src:url('sans.ttf')}
    @font-face{font-family:PilotSans;src:url('sans-bold.ttf');font-weight:700}
    @font-face{font-family:PilotSerif;src:url('serif.ttf')}
    *{box-sizing:border-box}body{margin:0;background:${scene.palette.shadow};font-family:PilotSans,sans-serif}
    #pilot{position:relative;width:${WIDTH}px;height:${HEIGHT}px;overflow:hidden;color:${scene.palette.light};background:${scene.palette.shadow}}
    #asset{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
    .veil{position:absolute;inset:0;background:linear-gradient(180deg,${scene.palette.shadow}f5 0%,${scene.palette.shadow}99 34%,transparent 62%,${scene.palette.shadow}f7 100%)}
    #copy{position:absolute;left:53px;top:163px;right:50px}
    .eyebrow{font-weight:700;color:${scene.palette.accent};font-size:16px;letter-spacing:2.8px}
    h1{font-family:PilotSerif,serif;font-size:63px;line-height:1.13;letter-spacing:-2px;margin:25px 0 21px;font-weight:400}
    .subtitle{font-size:16px;letter-spacing:1.8px;border-top:2px solid ${scene.palette.accent};padding-top:15px;display:inline-block}
    .credit{position:absolute;left:53px;bottom:86px;font-size:13px;letter-spacing:1px}
    .track{position:absolute;left:53px;right:53px;bottom:63px;height:2px;background:#ffffff37}
    #progress{height:100%;width:100%;background:${scene.palette.accent};transform-origin:left}
    #motif{width:90px;height:90px;position:absolute;right:42px;bottom:137px}
  </style></head><body>
  <div id="pilot" data-composition-id="pilot" data-start="0" data-duration="${seconds}" data-width="${WIDTH}" data-height="${HEIGHT}">
    <img id="asset" class="clip" src="background.jpg" data-start="0" data-duration="${seconds}" data-track-index="1" alt="">
    <div class="veil"></div><div id="copy"><div class="eyebrow">${escape(scene.label)}</div>
    <h1>${effect === 'lines-reveal'
      ? scene.title.map(line => '<span style="display:block;overflow:hidden"><span class="review-line" style="display:block">' + escape(line) + '</span></span>').join('')
      : scene.title.map(escape).join('<br>')}</h1><div class="subtitle">${escape(scene.subtitle)}</div></div>
    <div class="credit">${escape(scene.credit)}</div><div class="track"><div id="progress"></div></div>
    <div id="motif"></div>
  </div>
  <script src="gsap.min.js"></script>
  ${brand === 'beauty' ? '<script src="lottie.min.js"></script>' : ''}
  <script>
  window.__timelines = window.__timelines || {};
  const timeline = gsap.timeline({paused: true});
  timeline.fromTo('#asset',{scale:1.035},{scale:1.125,duration:${seconds},ease:'none'},0)
    .fromTo('#copy',{y:22,opacity:0},{y:0,opacity:1,duration:.65,ease:'power2.out'},.08)
    .fromTo('#progress',{scaleX:0},{scaleX:1,duration:${seconds},ease:'none'},0);
  ${effect === 'lines-reveal' ? `timeline.fromTo('.review-line',{y:${preset.distance_px},opacity:0},{y:0,opacity:1,duration:${preset.duration_ms / 1000},stagger:${preset.stagger_ms / 1000},ease:'expo.out'},.08);` : ''}
  ${effect === 'mask-reveal' ? `timeline.fromTo('#asset',{clipPath:'circle(0% at 50% 50%)'},{clipPath:'circle(75% at 50% 50%)',duration:${preset.duration_ms / 1000},ease:'expo.out'},0);` : ''}
  ${brand === 'beauty' ? `const state={frame:0};
    const motif=lottie.loadAnimation({container:document.getElementById('motif'),renderer:'svg',autoplay:false,loop:false,animationData:${JSON.stringify(moisture)}});
    motif.addEventListener('DOMLoaded',()=>motif.goToAndStop(state.frame,true));
    timeline.to(state,{frame:239,duration:${seconds},ease:'none',onUpdate:()=>motif.goToAndStop(state.frame,true)},0);` : ''}
  window.__timelines.pilot=timeline;
  </script></body></html>`;
  writeFileSync(join(directory, 'index.html'), content);
  copyFileSync(join(here, 'node_modules/gsap/dist/gsap.min.js'), join(directory, 'gsap.min.js'));
  for (const [name, file] of [['sans','DejaVuSans'], ['sans-bold','DejaVuSans-Bold'], ['serif','DejaVuSerif']]) {
    copyFileSync('/usr/share/fonts/truetype/dejavu/'+file+'.ttf', join(directory, name+'.ttf'));
  }
  if (brand === 'beauty') {
    copyFileSync(join(here, 'node_modules/lottie-web/build/player/lottie_svg.min.js'), join(directory, 'lottie.min.js'));
  }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  prepare(resolve(process.argv[2]), process.argv[3], process.argv[4]);
}
