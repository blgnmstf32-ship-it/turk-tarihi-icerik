import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {History3DScene, History3DKind, HistoricalOverlay} from './History3DScene';
import motionPresets from '../media_pilot/motion_presets.json';

type DepthLayer = {src: string; travelPx: number};
type OptionalEffect = 'lines-reveal' | 'mask-reveal';
const motionEasing = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const,
  easing: Easing.out(Easing.exp)};


export const WIDTH = 1080;
export const HEIGHT = 1920;
export const FPS = 30;

export type CaptionCue = {start: number; end: number; text: string};
export type DocumentaryProps = {
  durationSec: number;
  title?: string;
  scenes: {src: string; label?: string; depthLayers?: DepthLayer[]}[];
  captions: CaptionCue[];
  edit?: {title: string; topic: string; hook: string; effect?: OptionalEffect};
  threeScenes?: {kind: History3DKind; title: string; labels?: string[]; fromSec: number; durationSec: number; atlas?: HistoricalOverlay}[];
};

const Scene: React.FC<{
  src: string;
  index: number;
  duration: number;
  label?: string;
  dissolve?: number;
  depthLayers?: DepthLayer[];
  effect?: OptionalEffect;
}> = ({src, index, duration, label, dissolve = 0, depthLayers = [], effect}) => {
  const frame = useCurrentFrame();
  const local = frame;
  const motion = {extrapolateRight: 'clamp' as const, easing: Easing.inOut(Easing.cubic)};
  const scale = interpolate(local, [0, Math.max(1, duration)], index === 0 ? [1.32,1.13] :
    index % 2 ? [1.18,1.05] : [1.03,1.17], motion);
  const opacity = dissolve ? interpolate(local,[0,dissolve],[0,1],motion) : 1;
  const drift = interpolate(local, [0, Math.max(1, duration)], index % 2 ? [2.4,-1.1] : [-2,1.6], motion);
  const lift = interpolate(local,[0,Math.max(1,duration)],index % 3 === 0 ? [1,-2] : [-1,1],motion);
  const radius = interpolate(local, [0, motionPresets['mask-reveal'].duration_ms * FPS / 1000], [0, 75], motionEasing);
  const filter = 'saturate(0.84) contrast(1.09) brightness(0.93) sepia(.12)';
  const camera = `scale(${scale}) translate(${drift}%,${lift}%)`;
  return (
    <AbsoluteFill style={{opacity, overflow: 'hidden', backgroundColor: '#090d12'}}>
      <Img
        src={staticFile(src)}
        style={{width:'100%',height:'100%',objectFit:'cover',transform: camera, filter,
          clipPath: effect === 'mask-reveal' ? `circle(${radius}% at 50% 50%)` : undefined}}
      />
      {depthLayers.map((layer) => {
        const shift = interpolate(local, [0, Math.max(1, duration)], [-layer.travelPx, layer.travelPx], motion);
        return <Img key={layer.src} src={staticFile(layer.src)} style={{position:'absolute', inset:0,
          width:'100%', height:'100%', objectFit:'cover', filter,
          transform: `translateX(${shift}px) ${camera}`}} />;
      })}
      {label && <div style={{position:'absolute',top:135,left:54,color:'#faf0d7',font:'700 22px Arial',
        letterSpacing:3,background:'#102020',padding:'10px 14px'}}>{label}</div>}
    </AbsoluteFill>
  );
};

const ActiveCaption: React.FC<{captions: CaptionCue[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const second = frame / FPS;
  const cue = captions.find((item) => second >= item.start && second < item.end);
  if (!cue) return null;
  const words = cue.text.trim().split(/\s+/).filter(Boolean);
  const emphasis = /^(atlas|okyanus|piri|reis|gelibolu|kolomb|kayıp|kayna|harita|tutulma|antik|zafer|kaynak|oyun)/u;
  const accent = words.map(word => emphasis.test(word.toLocaleLowerCase('tr-TR').replace(/^[^\p{L}]+/u,'')));
  const enter = interpolate(second-cue.start,[0,.11],[7,0],{extrapolateRight:'clamp'});
  return (
    <div style={{display:'flex',flexWrap:'wrap',justifyContent:'center',gap:'0.07em 0.25em',maxWidth:'85%',
      padding:'16px 29px',borderRadius:12,background:'rgba(5,12,14,.88)',borderBottom:'3px solid #b69360',
      color:'#fffdf3',fontFamily:'Arial, sans-serif',fontWeight:750,fontSize:words.length>10?47:59,
      lineHeight:1.13,textAlign:'center',transform:`translateY(${enter}px)`,textShadow:'0 2px 8px #030609'}}>
      {words.map((word, i) => (
        <span key={`${i}-${word}`} style={{color:accent[i]?'#f3ca85':'#fffdf3',display:'inline-block'}}>{word}</span>
      ))}
    </div>
  );
};

export const DocumentaryReel: React.FC<DocumentaryProps> = ({durationSec, title = 'TARİHİN BİLİNMEYEN GERÇEKLERİ', scenes, captions, threeScenes = [], edit}) => {
  const frame = useCurrentFrame();
  const totalFrames = Math.ceil(durationSec * FPS);
  const lineProgress = interpolate(frame, [0, motionPresets['lines-reveal'].duration_ms * FPS / 1000],
    [0, 1], motionEasing);
  const usable = scenes.length ? scenes : [{src: 'placeholder.svg'}];
  const step = totalFrames / usable.length;
  return (
    <AbsoluteFill style={{backgroundColor: '#080b10', color: 'white'}}>
      {usable.map((scene, i) => {
        const from = Math.floor(i * step);
        const to = Math.min(totalFrames, Math.floor((i + 1) * step)+14);
        return <Sequence key={`${i}-${scene.src}`} from={from} durationInFrames={Math.max(1,to-from)}>
          <Scene src={scene.src} label={scene.label} index={i} duration={to-from} dissolve={i?14:0} depthLayers={scene.depthLayers} effect={i === 0 ? edit?.effect : undefined} />
        </Sequence>;
      })}
      {threeScenes.map((scene, i) => (
        <Sequence key={`three-${i}-${scene.kind}`} from={Math.round(scene.fromSec * FPS)} durationInFrames={Math.max(1, Math.round(scene.durationSec * FPS))}>
          <History3DScene kind={scene.kind} title={scene.title} labels={scene.labels} atlas={scene.atlas} />
        </Sequence>
      ))}
      <AbsoluteFill style={{background:'linear-gradient(180deg,#081317b2 0%,transparent 23%,transparent 55%,#07111556 75%,#071115ec 100%)',pointerEvents:'none'}} />
      <div style={{position:'absolute',top:72,left:54,borderLeft:'3px solid #c49a5d',paddingLeft:14,
        color:'#fff4dc',font:'700 20px Arial',letterSpacing:3}}>{title}</div>
      {edit && frame<81 && <div style={{position:'absolute',left:65,right:86,bottom:345,
        opacity:interpolate(frame,[0,8,67,81],[.8,1,1,0],{extrapolateRight:'clamp'}),
        textShadow:'0 3px 24px #061214,0 3px 55px #061214'}}>
        <div style={{font:'700 29px Arial',letterSpacing:5,color:'#f4ca84',marginBottom:21}}>
          {edit.topic==='piri-reis-kayip-kaynak'?'PİRİ REİS  /  1513':'TARİH BELGESELİ'}
        </div>
        <div style={{font:'bold 100px Georgia',lineHeight:1.03,color:'#fff4db',
          overflow: edit.effect === 'lines-reveal' ? 'hidden' : undefined}}>
          <div style={edit.effect === 'lines-reveal' ? {opacity:lineProgress,
            transform:`translateY(${(1-lineProgress)*motionPresets['lines-reveal'].distance_px}px)`} : undefined}>
            {edit.topic==='piri-reis-kayip-kaynak'?<>Bu haritanın<br/>kayıp bir kaynağı var.</>:edit.hook}
          </div>
        </div>
      </div>}
      {(!edit || frame>=81) && <div style={{position:'absolute',left:30,right:65,bottom:295,
        display:'flex',justifyContent:'center'}}><ActiveCaption captions={captions} /></div>}
      <div style={{position:'absolute',left:54,right:70,bottom:188,height:3,background:'rgba(255,255,255,.22)'}}>
        <Progress durationSec={durationSec} />
      </div>
    </AbsoluteFill>
  );
};

const Progress: React.FC<{durationSec: number}> = ({durationSec}) => {
  const frame = useCurrentFrame();
  const width = Math.min(100, (frame / (durationSec * FPS)) * 100);
  return <div style={{height: '100%', width: `${width}%`, background: '#f1c77e'}} />;
};
