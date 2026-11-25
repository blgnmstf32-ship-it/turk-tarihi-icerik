import React from 'react';
import {ThreeCanvas} from '@remotion/three';
import {interpolate, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {AbsoluteFill} from 'remotion';

export type History3DKind = 'battle_map' | 'city_flyover' | 'siege' | 'artifact_gears';
export type History3DSceneProps = {
  kind: History3DKind;
  title: string;
  labels?: string[];
};

const Ground: React.FC = () => (
  <>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.08, 0]} receiveShadow>
      <planeGeometry args={[42, 56]} />
      <meshStandardMaterial color="#28352e" roughness={1} />
    </mesh>
    <gridHelper args={[40, 32, '#758064', '#475448']} position={[0, 0, 0]} />
    {[[-11, -8], [-8, 5], [10, -7], [12, 8], [-3, 12], [6, 13], [-13, 1]].map(([x, z], i) => (
      <mesh key={i} position={[x, 0.35, z]} rotation={[0, i * 0.51, 0]}>
        <coneGeometry args={[1.4 + (i % 3) * 0.35, 2 + (i % 2), 5]} />
        <meshStandardMaterial color={i % 2 ? '#59614a' : '#747354'} roughness={1} />
      </mesh>
    ))}
  </>
);

const River: React.FC = () => {
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-13, 0.12, -1), new THREE.Vector3(-5, 0.12, -3),
    new THREE.Vector3(1, 0.12, 0), new THREE.Vector3(7, 0.12, 2),
    new THREE.Vector3(14, 0.12, 1),
  ]);
  return <mesh><tubeGeometry args={[curve, 48, 0.22, 7, false]} /><meshStandardMaterial color="#5f8990" roughness={0.5} /></mesh>;
};

const Route: React.FC<{from: [number, number]; to: [number, number]; color: string; progress: number; reverse?: boolean}> = ({from, to, color, progress, reverse = false}) => {
  const t = Math.max(0, Math.min(1, progress));
  const x = from[0] + (to[0] - from[0]) * t;
  const z = from[1] + (to[1] - from[1]) * t;
  const dx = to[0] - from[0];
  const dz = to[1] - from[1];
  const angle = Math.atan2(dx, dz);
  return (
    <>
      <mesh position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.065, 0.065, Math.hypot(dx, dz), 6]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.2} />
      </mesh>
      <mesh position={[x, 0.55, z]} rotation={[0, angle + (reverse ? Math.PI : 0), 0]}>
        <coneGeometry args={[0.38, 0.9, 5]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
      </mesh>
      {[-1.7, -0.9, 0.8, 1.6].map((offset, i) => (
        <mesh key={i} position={[x - Math.cos(angle) * offset, 0.28, z + Math.sin(angle) * offset]}>
          <boxGeometry args={[0.43, 0.35, 0.43]} />
          <meshStandardMaterial color={color} />
        </mesh>
      ))}
    </>
  );
};

const BattleMap: React.FC = () => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 9 * 30], [0.03, 0.98], {extrapolateRight: 'clamp'});
  const cameraZ = interpolate(frame, [0, 9 * 30], [14, 7], {extrapolateRight: 'clamp'});
  return (
    <ThreeCanvas width={1080} height={1920} dpr={1} orthographic={false}
      camera={{position: [0, 26, cameraZ], rotation: [1.1, 0, 0], fov: 37, near: 0.1, far: 120}}
      gl={{antialias: false, alpha: false}}>
      <color attach="background" args={['#17211e']} />
      <ambientLight intensity={1.5} />
      <directionalLight position={[-8, 18, 9]} intensity={2.4} />
      <Ground /><River />
      <mesh position={[0, 0.22, 0]}><cylinderGeometry args={[1.1, 1.4, 0.36, 8]} /><meshStandardMaterial color="#b59a69" /></mesh>
      <Route from={[-10, -8]} to={[0, 0]} color="#d9b35b" progress={p} />
      <Route from={[10, 8]} to={[0, 0]} color="#a9655c" progress={p} reverse />
    </ThreeCanvas>
  );
};

const City: React.FC<{siege: boolean}> = ({siege}) => {
  const frame = useCurrentFrame();
  const z = interpolate(frame, [0, 7 * 30], [20, 10], {extrapolateRight: 'clamp'});
  const cityBlocks: Array<[number, number, number]> = [];
  for (let row = -3; row <= 3; row++) for (let col = -3; col <= 3; col++) {
    if (Math.abs(row) === 3 || Math.abs(col) === 3) continue;
    cityBlocks.push([col * 1.6, row * 1.6, 0.7 + ((row + col + 10) % 3) * 0.35]);
  }
  return (
    <ThreeCanvas width={1080} height={1920} dpr={1} camera={{position: [0, 23, z], rotation: [1.03, 0, 0], fov: 39, near: 0.1, far: 120}} gl={{antialias: false, alpha: false}}>
      <color attach="background" args={['#1b2426']} />
      <ambientLight intensity={1.4} /><directionalLight position={[-7, 18, 11]} intensity={2.2} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}><planeGeometry args={[40, 48]} /><meshStandardMaterial color="#343b31" roughness={1} /></mesh>
      {cityBlocks.map(([x, zz, h], i) => <mesh key={i} position={[x, h / 2, zz]}>
        <boxGeometry args={[1.25, h, 1.2]} /><meshStandardMaterial color={i % 3 ? '#a69373' : '#82765e'} roughness={0.92} />
      </mesh>)}
      {[[-6, 0], [6, 0], [0, -6], [0, 6]].map(([x, zz], i) => <mesh key={`wall-${i}`} position={[x, 1.1, zz]}>
        <boxGeometry args={i < 2 ? [0.5, 2.2, 13] : [13, 2.2, 0.5]} /><meshStandardMaterial color="#baaa88" />
      </mesh>)}
      {[-5.5, -1.8, 1.8, 5.5].map((x, i) => <mesh key={`tower-${i}`} position={[x, 1.6, -5.5]}>
        <cylinderGeometry args={[0.72, 0.82, 3.2, 8]} /><meshStandardMaterial color="#ccb590" />
      </mesh>)}
      {siege && [-1.2, 0, 1.2].map((x, i) => <mesh key={`siege-${i}`} position={[x + (i - 1) * 7, 0.55, 9]}>
        <boxGeometry args={[1.15, 1.1, 1.15]} /><meshStandardMaterial color="#a9655c" />
      </mesh>)}
    </ThreeCanvas>
  );
};

// A simplified gear pair for explanation. It does not reconstruct the artifact.
const Gear: React.FC<{x: number; y: number; radius: number; teeth: number; angle: number; color: string}> = ({x, y, radius, teeth, angle, color}) => (
  <group position={[x, y, 0]} rotation={[0, 0, angle]}>
    <mesh><torusGeometry args={[radius - 0.18, 0.36, 8, 48]} /><meshStandardMaterial color={color} metalness={0.65} roughness={0.46} /></mesh>
    {Array.from({length: teeth}, (_, i) => {
      const a = (i / teeth) * 2 * Math.PI;
      return <mesh key={i} position={[radius * Math.cos(a), radius * Math.sin(a), 0]} rotation={[0, 0, a]}>
        <boxGeometry args={[0.62, 0.34, 0.53]} /><meshStandardMaterial color={color} metalness={0.65} roughness={0.46} />
      </mesh>;
    })}
    {[0, 1, 2].map(i => <mesh key={i} rotation={[0, 0, i * Math.PI / 3]}>
      <boxGeometry args={[radius * 1.65, 0.26, 0.5]} /><meshStandardMaterial color={color} />
    </mesh>)}
  </group>
);

const ArtifactGears: React.FC = () => {
  const frame = useCurrentFrame();
  const angle = interpolate(frame, [0, 240], [-0.28, 0.14], {extrapolateRight: 'clamp'});
  return <ThreeCanvas width={1080} height={1920} dpr={1} camera={{position: [0, 1.1, 16 - frame / 250], fov: 53}} gl={{antialias: true}}>
    <color attach="background" args={['#101c20']} />
    <ambientLight intensity={1.2} />
    <directionalLight position={[-5, 7, 12]} intensity={3.4} />
    <directionalLight position={[4, -2, 3]} intensity={1.1} color="#99c8e4" />
    <group rotation={[-0.24, angle, -0.42]}>
      <Gear x={-1.8} y={0.7} radius={2.3} teeth={22} angle={frame / 80} color="#c4935a" />
      <Gear x={2.15} y={0.7} radius={1.65} teeth={16} angle={-frame / 80 * 22 / 16} color="#8fa698" />
    </group>
  </ThreeCanvas>;
};

export const History3DScene: React.FC<History3DSceneProps> = ({kind, title, labels = []}) => (
  <AbsoluteFill style={{backgroundColor: '#17211e'}}>
    {kind === 'battle_map' ? <BattleMap /> : kind === 'artifact_gears' ? <ArtifactGears /> : <City siege={kind === 'siege'} />}
    <div style={{position: 'absolute', left: 30, right: 30, top: 130, textAlign: 'center', color: '#fff0d4', font: '800 32px Arial, sans-serif', letterSpacing: 1.5, textShadow: '0 3px 14px #000', background: 'rgba(5,9,12,.56)', borderRadius: 12, padding: '14px 18px'}}>{title}</div>
    <div style={{position: 'absolute', left: 24, right: 24, top: 210, display: 'flex', justifyContent: 'space-evenly', gap: 12}}>
      {labels.map((label) => <span key={label} style={{font: '700 21px Arial, sans-serif', letterSpacing: 0.5, color: '#fff2d5', background: 'rgba(6,9,11,.72)', padding: '9px 12px', borderRadius: 9}}>{label}</span>)}
    </div>
  </AbsoluteFill>
);
