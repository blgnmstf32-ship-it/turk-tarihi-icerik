import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {z} from 'zod';
import {DocumentaryReel, DocumentaryProps, FPS, HEIGHT, WIDTH} from './DocumentaryReel';
import {BeautySkinScene} from './BeautySkinScene';
import {History3DScene} from './History3DScene';

const schema = z.object({
  durationSec: z.number(),
  title: z.string().optional(),
  scenes: z.array(z.object({src: z.string(), label: z.string().optional()})),
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  edit: z.object({title: z.string(), topic: z.string(), hook: z.string()}).optional(),
  threeScenes: z.array(z.object({kind: z.enum(['battle_map', 'city_flyover', 'siege', 'artifact_gears', 'atlantic_atlas']), title: z.string(), labels: z.array(z.string()).optional(), fromSec: z.number(), durationSec: z.number()})).optional(),
});

const Root: React.FC = () => (
  <>
  <Composition<typeof schema, DocumentaryProps>
    id="DocumentaryReel"
    component={DocumentaryReel}
    width={WIDTH}
    height={HEIGHT}
    fps={FPS}
    durationInFrames={1}
    schema={schema}
    defaultProps={{durationSec: 60, scenes: [], captions: [], threeScenes: []}}
    calculateMetadata={({props}) => ({durationInFrames: Math.ceil(props.durationSec * FPS)})}
  />
  <Composition id="BeautySkinBarrier" component={BeautySkinScene} width={540} height={960}
    fps={24} durationInFrames={192} defaultProps={{kind: 'barrier'}} />
  <Composition id="BeautyCream" component={BeautySkinScene} width={540} height={960}
    fps={24} durationInFrames={192} defaultProps={{kind: 'cream'}} />
  <Composition id="History3DPreview" component={History3DScene} width={WIDTH} height={HEIGHT} fps={FPS} durationInFrames={9 * FPS}
    defaultProps={{kind: 'battle_map', title: 'KUŞBAKIŞI 3D SAVAŞ HARİTASI', labels: ['SELÇUKLU ORDUSU', 'BİZANS ORDUSU']}} />
  </>
);

registerRoot(Root);
