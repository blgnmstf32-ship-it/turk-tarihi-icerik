import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export type DrawingBrand = 'tarih' | 'bakim';

const designs = {
  tarih: {
    body: 'M45 110 L40 50 Q72 40 100 63 Q126 42 161 53 L155 115 Q125 105 100 129 Q73 105 45 110Z',
    detail: 'M100 66 L100 127 M51 90 Q71 86 90 100 M110 92 Q129 79 150 82',
    ink: '#503423', fill: '#efc78e', line: '#a25e3f',
    label: 'TEMSİLÎ ÇİZİM',
  },
  bakim: {
    body: 'M102 43 C118 67 149 84 147 111 C143 144 104 154 79 137 C53 123 60 98 74 78 Q89 62 102 43Z',
    detail: 'M68 108 Q73 125 91 132 M117 69 Q131 84 134 98',
    ink: '#5b344b', fill: '#f8bdad', line: '#a95873',
    label: 'EĞİTİCİ ÇİZİM',
  },
};

export const characterPose = (frame: number, duration: number) => {
  const t = Math.min(1, Math.max(0, frame / Math.max(1, duration - 1)));
  const gesture = Math.sin(Math.PI * t);
  return {
    lift: -7 * Math.sin(2 * Math.PI * t) * gesture,
    tilt: -6 + 12 * gesture,
    wave: 18 * gesture * (1 + Math.sin(5 * Math.PI * t)),
    blink: Math.abs(t - .58) < .035,
    opacity: interpolate(t, [0, .1, .88, 1], [0, 1, 1, 0]),
  };
};

export const EditorialCharacter: React.FC<{brand: DrawingBrand}> = ({brand}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const style = designs[brand];
  const pose = characterPose(frame, durationInFrames);
  return <AbsoluteFill style={{pointerEvents: 'none', opacity: pose.opacity}}>
    <svg viewBox="0 0 200 164" aria-hidden="true" style={{position:'absolute', right:'7%',
      bottom:'30%', width:'32%', overflow:'visible'}}>
      <g transform={`translate(0 ${pose.lift}) rotate(${pose.tilt} 100 96)`}
        stroke={style.ink} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M58 107 Q37 101 28 83 M80 126 Q77 140 66 143 M121 127 Q124 141 136 143" fill="none"/>
        <path d="M140 103 Q159 104 173 85" fill="none"
          transform={`rotate(${pose.wave} 140 103)`}/>
        <path d={style.body} fill={style.fill}/>
        <path d={style.detail} stroke={style.line} fill="none" strokeWidth="2"/>
        {[82, 115].map(x => <ellipse key={x} cx={x} cy="90" rx="2.6" ry={pose.blink ? .6 : 3.4}
          fill={style.ink} stroke="none"/>)}
        <path d="M93 104 Q100 111 108 104" fill="none" strokeWidth="2.3"/>
      </g>
    </svg>
    <div style={{position:'absolute', right:'8%', bottom:'29%', background:style.ink,
      padding:'5px 10px', color:'#fff5e7', font:'700 20px sans-serif'}}>{style.label}</div>
  </AbsoluteFill>;
};
