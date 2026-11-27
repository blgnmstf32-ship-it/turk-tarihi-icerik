import React from 'react';
import {AbsoluteFill, Composition, Html5Audio, Img, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {BeautySkinScene} from './BeautySkinScene';

const shotSchema = z.object({
  id: z.string(), start: z.number(), end: z.number(),
  kind: z.enum(['flat', 'science', 'motion', 'barrier', 'macro']), motif: z.string(), heading: z.string(),
  purpose: z.string(), insert: z.number(), src: z.string().nullable(),
});
const schema = z.object({
  title: z.string(), frames: z.number(), audio: z.string(), openingEffect: z.boolean(), shots: z.array(shotSchema),
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
});
type Shot = z.infer<typeof shotSchema>;
type Props = z.infer<typeof schema>;

const colors = {plum: '#27182d', panel: '#3d263e', pink: '#ffc8bb', cream: '#fff1e9', lavender: '#d6c2f6'};
const sans = 'DejaVu Sans, sans-serif';
const serif = 'DejaVu Serif, serif';
const fps = 30;

const Graphic: React.FC<{motif: string}> = ({motif}) => {
  const frame = useCurrentFrame();
  const rise = interpolate(frame, [0, 18], [30, 0], {extrapolateRight: 'clamp'});
  const diagram = {position: 'absolute', inset: '400px 132px 510px', borderRadius: 88,
    border: '2px solid #79556f', background: colors.panel, display: 'flex', justifyContent: 'center',
    alignItems: 'center', gap: 20, transform: `translateY(${rise}px)`} as const;
  if (motif === 'uv') {
    return <div style={diagram}>{['UVA', 'UVB'].map((band, i) => <div key={band} style={{padding: '32px 38px',
      borderRadius: 44, background: i ? colors.lavender : colors.pink, color: colors.plum,
      fontFamily: sans, fontSize: 64, fontWeight: 700}}>{band}</div>)}</div>;
  }
  if (motif === 'follicle' || motif === 'hair') {
    return <div style={diagram}>
      <div style={{position: 'absolute', top: '52%', width: '75%', height: '24%', borderRadius: 28, background: '#b87783'}} />
      {[0, 1, 2].map(i => <div key={i} style={{width: 68, height: 330 - 25 * i, border: `6px solid ${colors.pink}`,
        borderTopWidth: 0, borderRadius: '0 0 90px 90px', transform: `rotate(${i * 14 - 14}deg)`}} />)}
    </div>;
  }
  if (motif === 'layers' || motif === 'label' || motif === 'sources' || motif === 'recap') {
    return <div style={{...diagram, flexDirection: 'column'}}>{[0, 1, 2].map(i => <div key={i} style={{
      width: 420 - 52 * i, height: motif === 'layers' ? 52 : 24, borderRadius: 30, background: i % 2 ? colors.lavender : colors.pink,
      opacity: interpolate(frame, [i * 5, i * 5 + 12], [.25, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />)}</div>;
  }
  return <div style={diagram}>
    <div style={{width: 290, height: 290, border: `4px solid ${colors.pink}`, borderRadius: '50%', display: 'grid',
      placeItems: 'center', background: '#532f4a', color: colors.cream, fontFamily: serif, fontSize: 138}}>
      {motif === 'caution' ? '!' : <div style={{width: 120, height: 120, transform: 'rotate(-45deg)',
        background: colors.lavender, borderRadius: '0 65% 65% 65%'}} />}
    </div>
  </div>;
};

const BeautyShot: React.FC<{shot: Shot; title: string; reveal: boolean}> = ({shot, title, reveal}) => {
  const model = shot.kind === 'barrier' ? 'barrier' : shot.kind === 'macro' ? 'cream' : null;
  const frame = useCurrentFrame();
  const zoom = 1 + Math.min(frame, 170) / 1700;
  const entry = reveal ? interpolate(frame, [0, 14], [32, 0], {extrapolateRight: 'clamp'}) : 0;
  const heading = shot.purpose === 'safety' ? 'SAĞLIK UYARISI' : shot.purpose === 'sources' ? 'KAYNAK' : title;
  return <AbsoluteFill style={{background: colors.plum, color: colors.cream, fontFamily: sans}}>
    {shot.src ? <Img src={staticFile(shot.src)} style={{position: 'absolute', top: 345, left: 122, width: 836,
      height: 1060, objectFit: 'cover', borderRadius: 56, transform: `scale(${zoom})`}} /> : <Graphic motif={shot.motif} />}
    {model && <Sequence from={0} durationInFrames={shot.insert} layout="none">
      <AbsoluteFill style={{overflow: 'hidden', clipPath: 'inset(19% 9% 22% round 6%)'}}>
        <BeautySkinScene kind={model} continuous />
      </AbsoluteFill>
    </Sequence>}
    <div style={{position: 'absolute', top: 164, left: 112, right: 112, fontSize: 30, color: colors.pink,
      letterSpacing: 3}}>{heading}</div>
    <div style={{position: 'absolute', top: 229, left: 112, right: 112, fontSize: 75, fontFamily: serif,
      lineHeight: 1.08, transform: `translateY(${entry}px)`, textShadow: `0 5px 18px ${colors.plum}`}}>{shot.heading}</div>
    <div style={{position: 'absolute', left: 116, bottom: 392, fontSize: 25, padding: '12px 19px', borderRadius: 14,
      background: colors.plum, color: colors.pink}}>{shot.src ? 'TEMSİLÎ GÖRSEL' : 'TEMSİLÎ ŞEMA · ÖLÇEK DIŞI'}</div>
  </AbsoluteFill>;
};

const BeautyReel: React.FC<Props> = ({title, audio, captions, shots, openingEffect}) => {
  const time = useCurrentFrame() / fps;
  const caption = captions.find(cue => cue.start <= time && time < cue.end);
  return <AbsoluteFill>
    {audio && <Html5Audio src={staticFile(audio)} />}
    {shots.map(shot => <Sequence key={shot.id} from={shot.start} durationInFrames={shot.end - shot.start}>
      <BeautyShot shot={shot} title={title} reveal={openingEffect && shot.start === 0} />
    </Sequence>)}
    {caption && <div style={{position: 'absolute', left: 118, right: 118, bottom: 222, fontFamily: sans,
      fontSize: 52, lineHeight: 1.18, textAlign: 'center', color: colors.cream, fontWeight: 700,
      background: '#211321eb', borderRadius: 30, padding: '20px 28px'}}>{caption.text}</div>}
  </AbsoluteFill>;
};

const Root: React.FC = () => <Composition id="GeneralBeautyReel" component={BeautyReel} width={1080} height={1920}
  fps={fps} durationInFrames={1} schema={schema}
  defaultProps={{title: 'Güzellik ve Kişisel Bakım', frames: 2100, audio: '', openingEffect: false, shots: [], captions: []}}
  calculateMetadata={({props}) => ({durationInFrames: props.frames})} />;

registerRoot(Root);
