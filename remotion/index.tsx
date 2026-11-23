import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {z} from 'zod';
import {DocumentaryReel, DocumentaryProps, FPS, HEIGHT, WIDTH} from './DocumentaryReel';

const schema = z.object({
  durationSec: z.number(),
  title: z.string().optional(),
  scenes: z.array(z.object({src: z.string(), label: z.string().optional()})),
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
});

const Root: React.FC = () => (
  <Composition<typeof schema, DocumentaryProps>
    id="DocumentaryReel"
    component={DocumentaryReel}
    width={WIDTH}
    height={HEIGHT}
    fps={FPS}
    durationInFrames={1}
    schema={schema}
    defaultProps={{durationSec: 60, scenes: [], captions: []}}
    calculateMetadata={({props}) => ({durationInFrames: Math.ceil(props.durationSec * FPS)})}
  />
);

registerRoot(Root);
