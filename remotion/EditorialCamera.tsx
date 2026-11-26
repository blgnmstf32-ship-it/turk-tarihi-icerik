import {useLayoutEffect} from 'react';
import {useThree} from '@react-three/fiber';
import {cameraPose, type CameraTrack} from './editorialCamera';

export const EditorialCamera = ({track, progress}: {track: CameraTrack; progress: number}) => {
  const camera = useThree(state => state.camera);
  useLayoutEffect(() => {
    const pose = cameraPose(track, progress);
    camera.position.copy(pose.position);
    camera.lookAt(pose.focus);
    camera.updateMatrixWorld(true);
  }, [camera, track, progress]);
  return null;
};
