import React, {useEffect, useRef} from 'react';
import {AbsoluteFill, Composition, Easing, Img, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import lottie, {AnimationItem} from 'lottie-web';
import {moisture} from './moisture.mjs';

type Scene = {
  label: string; title: string[]; subtitle: string; credit: string;
  palette: {light: string; accent: string; shadow: string}; seconds: number; animation: string;
};

const Preview = (scene: Scene) => {
  const frame = useCurrentFrame();
  const time = frame / 30;
  const opacity = interpolate(time,[.08,.73],[0,1],{easing:Easing.out(Easing.cubic),extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const box = useRef<HTMLDivElement>(null);
  const motion = useRef<AnimationItem | null>(null);
  const index = Math.floor(239*time/scene.seconds);
  useEffect(() => {
    if (!box.current) return;
    const effect = lottie.loadAnimation({container:box.current,renderer:'svg',loop:false,autoplay:false,animationData:moisture});
    motion.current = effect;
    effect.goToAndStop(index,true);
    return () => { motion.current = null; effect.destroy(); };
  }, []);
  useEffect(() => { motion.current?.goToAndStop(index,true); }, [index]);
  const p = scene.palette;
  return <AbsoluteFill style={{color:p.light,background:p.shadow,fontFamily:'DejaVu Sans, sans-serif',overflow:'hidden'}}>
    <Img src={staticFile('background.jpg')} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',transform:`scale(${1.035+.09*time/scene.seconds})`}} />
    <AbsoluteFill style={{background:`linear-gradient(180deg,${p.shadow}f5 0%,${p.shadow}99 34%,transparent 62%,${p.shadow}f7 100%)`}}/>
    <div style={{position:'absolute',left:53,top:163,right:50,opacity,transform:`translateY(${22*(1-opacity)}px)`}}>
      <div style={{fontWeight:700,color:p.accent,fontSize:16,letterSpacing:2.8}}>{scene.label}</div>
      <h1 style={{fontFamily:'DejaVu Serif, serif',fontSize:63,lineHeight:1.13,letterSpacing:-2,margin:'25px 0 21px',fontWeight:400}}>{scene.title.map((part,i)=><React.Fragment key={part}>{i>0&&<br/>}{part}</React.Fragment>)}</h1>
      <div style={{fontSize:16,letterSpacing:1.8,borderTop:`2px solid ${p.accent}`,paddingTop:15,display:'inline-block'}}>{scene.subtitle}</div>
    </div>
    <div style={{position:'absolute',left:53,bottom:86,fontSize:13,letterSpacing:1}}>{scene.credit}</div>
    <div style={{position:'absolute',left:53,right:53,bottom:63,height:2,background:'#ffffff37'}}>
      <div style={{height:2,width:`${100*time/scene.seconds}%`,background:p.accent}}/>
    </div>
    {scene.animation==='lottie_moisture_pulse' && <div ref={box} style={{width:90,height:90,position:'absolute',right:42,bottom:137}} />}
  </AbsoluteFill>;
};

const Studio = () => <Composition id="MediaPilot" component={Preview} fps={30} width={720} height={1280}
  durationInFrames={240} calculateMetadata={({props})=>({durationInFrames:Math.round(props.seconds*30)})}
  defaultProps={{label:'',title:[],subtitle:'',credit:'',palette:{light:'#fff',accent:'#fff',shadow:'#000'},seconds:8,animation:''}}/>;
registerRoot(Studio);
