import React from 'react';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {EditorialCamera} from './EditorialCamera';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';

type SceneKind = 'barrier' | 'cream';
export type BeautySceneProps = {kind: SceneKind; continuous?: boolean};

const tile = new RoundedBoxGeometry(0.66, 0.14, 0.49, 2, 0.064);
const plum = '#281525';
const rose = ['#efaa9f', '#d28b82', '#f2c1a2', '#df9b8e'];

const Camera: React.FC<{t: number; kind: SceneKind}> = ({t, kind}) => {
  const camera = useThree((state) => state.camera);
  const angle = interpolate(t, [0, 1], kind === 'barrier' ? [0.60, 0.23] : [0.51, -0.20]);
  const radius = interpolate(t, [0, 1], [8.5, 7.6]);
  camera.position.set(radius * Math.sin(angle), 4.0 - 1.3 * t, radius * Math.cos(angle));
  camera.lookAt(0, -0.30, 0);
  camera.updateMatrixWorld();
  return null;
};

const Barrier: React.FC<{t: number}> = ({t}) => (
  <>
    <mesh position={[0, -0.28, 0]}>
      <boxGeometry args={[4.05, .42, 2.86]} />
      <meshStandardMaterial color="#993f56" roughness={0.77} />
    </mesh>
    {Array.from({length: 60}, (_, i) => {
      const layer = Math.floor(i / 30);
      const row = Math.floor(i / 6) % 5;
      const column = i % 6;
      return <mesh key={i} geometry={tile}
        position={[(column - 2.5) * .66 + ((row + layer) % 2 ? .13 : -.13), layer*.135, (row-2)*.52]}
        rotation={[0, Math.sin(i * 8) * .04, 0]}>
        <meshStandardMaterial color={rose[i % rose.length]} roughness={0.43} />
      </mesh>;
    })}
    <mesh position={[0, .32, 0]} scale={[1, .045, .72]}>
      <sphereGeometry args={[1.9, 48, 24]} />
      <meshPhysicalMaterial color="#f3d7a8" opacity={.38 * Math.min(1, t * 6)} transparent
        metalness={.16} roughness={.26} clearcoat={.9} depthWrite={false} />
    </mesh>
    {Array.from({length: 16}, (_, i) => {
      const progress = (0.18 + t * .61 + i * .17) % 1;
      return <mesh key={i} position={[
        (i % 5 - 2) * .66 + .07 * Math.sin(i + progress * 8),
        .35 + progress * (1.1 + .09 * (i % 4)),
        (Math.floor(i / 5) - 1.5) * .61,
      ]} scale={Math.sin(Math.PI * progress) * (.85 + .14 * (i % 4))}>
        <sphereGeometry args={[.075, 16, 12]} />
        <meshPhysicalMaterial color="#a9ddea" roughness={.20} metalness={.35} clearcoat={1}
          opacity={.73 * Math.sin(Math.PI * progress)} transparent depthWrite={false} />
      </mesh>;
    })}
  </>
);

const Cream: React.FC<{t: number}> = ({t}) => {
  const lift = interpolate(t, [0, .68, 1], [.08, .82, .88], {easing: Easing.out(Easing.cubic)});
  return (
    <>
      <mesh position={[0, -.61, 0]}><cylinderGeometry args={[1.88, 1.88, .12, 72]} />
        <meshStandardMaterial color="#633950" roughness={.52} /></mesh>
      <mesh position={[0, -.02, 0]}><cylinderGeometry args={[1.20, 1.14, .98, 80]} />
        <meshPhysicalMaterial color="#ead4c0" roughness={.39} clearcoat={.5} /></mesh>
      <mesh position={[0, .49, 0]}><cylinderGeometry args={[1.11, 1.11, .04, 80]} />
        <meshPhysicalMaterial color="#ffecce" roughness={.29} clearcoat={.8} /></mesh>
      <mesh position={[0, .64 + lift, 0]} rotation={[.18*t, -.20*t, -.14*t]}><cylinderGeometry args={[1.23, 1.23, .23, 80]} />
        <meshStandardMaterial color="#ad7459" roughness={.41} metalness={.32} /></mesh>
      <mesh position={[0, -.19, 0]}><cylinderGeometry args={[1.195, 1.191, .25, 80]} />
        <meshStandardMaterial color="#b97f85" roughness={.61} /></mesh>
    </>
  );
};

export const BeautySkinScene: React.FC<BeautySceneProps> = ({kind, continuous = false}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const t = frame / Math.max(1, durationInFrames - 1);
  return (
    <AbsoluteFill style={{background: plum}}>
      <ThreeCanvas width={width} height={height} dpr={1}
        camera={{fov: 44, near: .1, far: 42}} gl={{antialias: true, alpha: false}}>
        <color attach="background" args={[plum]} />
        {continuous ? <EditorialCamera track={kind} progress={t} /> : <Camera t={t} kind={kind} />}
        <hemisphereLight args={['#fff2e8', '#655478', 1.8]} />
        <directionalLight position={[-4, 8, 7]} color="#ffdfcc" intensity={3.0} />
        <directionalLight position={[3, 5, -5]} color="#b8b3fc" intensity={2.55} />
        {kind === 'barrier' ? <Barrier t={t} /> : <Cream t={t} />}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
