import React from 'react';
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';

export const WIDTH = 1080;
export const HEIGHT = 1920;
export const FPS = 30;
// Clear editorial cuts keep scene changes legible and machine-auditable.

export type CaptionCue = {start: number; end: number; text: string};
export type DocumentaryProps = {
  durationSec: number;
  title?: string;
  scenes: {src: string; label?: string}[];
  captions: CaptionCue[];
};

const Scene: React.FC<{
  src: string;
  index: number;
  duration: number;
}> = ({src, index, duration}) => {
  const frame = useCurrentFrame();
  const local = frame;
  const scale = interpolate(local, [0, Math.max(1, duration)], index % 2 ? [1.08, 1] : [1, 1.08], {extrapolateRight: 'clamp'});
  const opacity = 1;
  const drift = interpolate(local, [0, Math.max(1, duration)], index % 2 ? [1.2, -1.2] : [-1.2, 1.2], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity, overflow: 'hidden', backgroundColor: '#090d12'}}>
      <Img
        src={staticFile(src)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale}) translateX(${drift}%)`, filter: 'saturate(0.9) contrast(1.06) brightness(0.78)'}}
      />
    </AbsoluteFill>
  );
};

const ActiveCaption: React.FC<{captions: CaptionCue[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const second = frame / FPS;
  const cue = captions.find((item) => second >= item.start && second < item.end);
  if (!cue) return null;
  const words = cue.text.trim().split(/\s+/).filter(Boolean);
  const progress = Math.max(0, Math.min(0.999, (second - cue.start) / Math.max(0.05, cue.end - cue.start)));
  const weight = words.map((word) => Math.max(2, word.replace(/[^\p{L}\p{N}]/gu, '').length));
  const total = weight.reduce((sum, value) => sum + value, 0);
  let elapsed = 0;
  const active = weight.findIndex((value) => {
    const before = elapsed;
    elapsed += value;
    return progress * total >= before && progress * total < elapsed;
  });
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0.18em 0.28em', maxWidth: '92%', padding: '18px 24px', borderRadius: 18, background: 'rgba(5,8,12,0.76)', color: '#fff', fontFamily: 'Arial, sans-serif', fontWeight: 900, fontSize: 66, lineHeight: 1.12, textAlign: 'center', textShadow: '0 3px 12px rgba(0,0,0,.9)', boxShadow: '0 8px 30px rgba(0,0,0,.2)'}}>
      {words.map((word, i) => (
        <span key={`${i}-${word}`} style={{color: i === active ? '#ffd47d' : '#fff', transform: i === active ? 'scale(1.06)' : 'scale(1)', transition: 'color 120ms linear, transform 120ms ease', display: 'inline-block'}}>{word}</span>
      ))}
    </div>
  );
};

export const DocumentaryReel: React.FC<DocumentaryProps> = ({durationSec, title = 'TÜRK TARİHİ', scenes, captions}) => {
  const totalFrames = Math.ceil(durationSec * FPS);
  const usable = scenes.length ? scenes : [{src: 'placeholder.svg'}];
  const step = totalFrames / usable.length;
  return (
    <AbsoluteFill style={{backgroundColor: '#080b10', color: 'white'}}>
      {usable.map((scene, i) => {
        const from = Math.floor(i * step);
        const to = Math.min(totalFrames, Math.ceil((i + 1) * step));
        return <Sequence key={`${i}-${scene.src}`} from={from} durationInFrames={Math.max(1, to - from)}><Scene src={scene.src} index={i} duration={to - from} /></Sequence>;
      })}
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,.34) 0%, transparent 26%, transparent 55%, rgba(0,0,0,.20) 72%, rgba(0,0,0,.76) 100%)', pointerEvents: 'none'}} />
      <div style={{position: 'absolute', top: 42, left: 35, padding: '9px 14px', borderRadius: 8, background: 'rgba(0,0,0,.38)', fontFamily: 'Arial, sans-serif', fontSize: 20, fontWeight: 700, letterSpacing: 2}}>{title}</div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 250, display: 'flex', justifyContent: 'center'}}><ActiveCaption captions={captions} /></div>
      <div style={{position: 'absolute', left: 34, right: 34, bottom: 64, height: 3, background: 'rgba(255,255,255,.25)'}}>
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
