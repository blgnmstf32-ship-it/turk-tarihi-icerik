import {gsap} from 'gsap';
import {CatmullRomCurve3, Vector3} from 'three';

type Point = [number, number, number];
export type CameraTrack = 'city' | 'battle' | 'atlas' | 'gears' | 'barrier' | 'cream';

const controls: Record<CameraTrack, {position: Point[]; focus: Point[]}> = {
  city: {position: [[-6, 24, 17], [-3.4, 22.5, 15.5], [0.2, 21, 12], [3.7, 19, 9.5]],
    focus: [[-1.8, .2, -1], [-1, .4, -.8], [1, .5, -1.1], [1.7, .6, -1.2]]},
  battle: {position: [[-4.5, 26, 14], [-2.4, 25, 12.5], [0.4, 24, 10.3], [2.6, 23, 8.9]],
    focus: [[-1.2, 0, -.6], [-.5, .15, -.65], [.25, .2, -.3], [.7, .2, 0]]},
  atlas: {position: [[-2.0, .7, 23], [-.9, .45, 22], [.6, .2, 20.4], [1.7, -.2, 19]],
    focus: [[-.55, .8, 0], [-.25, .8, 0], [.25, .95, 0], [.6, 1, 0]]},
  gears: {position: [[-2.6, 2, 16.9], [-1.4, 1.8, 16.3], [.65, 1.4, 15.3], [1.85, 1.0, 14.9]],
    focus: [[-1, .55, 0], [-.5, .55, 0], [.25, .58, 0], [.75, .64, 0]]},
  barrier: {position: [[4.3, 4, 7.1], [3.55, 3.65, 7.15], [2.65, 3.2, 7.2], [1.65, 2.7, 7.3]],
    focus: [[-.22, -.28, 0], [-.14, -.25, 0], [.03, -.15, 0], [.2, -.14, 0]]},
  cream: {position: [[4.15, 4, 7.35], [2.6, 3.65, 7.7], [.7, 3.2, 7.8], [-1.45, 2.85, 7.55]],
    focus: [[-.14, -.23, 0], [-.05, -.10, 0], [.07, .0, 0], [.14, .10, 0]]},
};
const curve = (points: Point[]) => new CatmullRomCurve3(points.map(point => new Vector3(...point)));
const paths = Object.fromEntries(Object.entries(controls).map(([id, p]) => [id, {
  position: curve(p.position), focus: curve(p.focus),
}])) as Record<CameraTrack, {position: CatmullRomCurve3; focus: CatmullRomCurve3}>;

const ease = gsap.parseEase('sine.inOut');

export function cameraPose(track: CameraTrack, progress: number) {
  // Sampling does not depend on elapsed wall time or the order Remotion asks for frames.
  const t = ease(Math.min(1, Math.max(0, progress)));
  const path = paths[track];
  return {position: path.position.getPointAt(t), focus: path.focus.getPointAt(t)};
}
