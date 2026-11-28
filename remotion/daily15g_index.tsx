import React from 'react';
import {AbsoluteFill, Composition, Img, OffthreadVideo, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import {z} from 'zod';

const shot = z.object({id:z.string(), start:z.number(), end:z.number(), title:z.string(), proof:z.array(z.string()),
  image:z.string().nullable(), footage:z.string().nullable(), label:z.string(), credit:z.string(), rate:z.number(), layout:z.number()});
const cue = z.object({start:z.number(), end:z.number(), text:z.string(), wordStarts:z.array(z.number())});
const schema = z.object({brand:z.enum(['tarih','bakim']), frames:z.number(), shots:z.array(shot), captions:z.array(cue)});
type Props = z.infer<typeof schema>;
type Shot = z.infer<typeof shot>;
const fps = 30;
const themes = {
  tarih:[['#101e26','#2d5656','#d9c18b'],['#291e1a','#69472d','#f7d199'],['#151d36','#444e75','#c0d4f2'],['#261d27','#60425a','#f3ceae'],['#142d29','#376c58','#b5f0d5']],
  bakim:[['#281c2d','#805971','#ffdae7'],['#142923','#486f5b','#c6f1d6'],['#291e3b','#65508c','#e6dcff'],['#3a2225','#885760','#ffded0'],['#22283d','#5868a0','#e0e6ff']],
};

const Scene: React.FC<{shot:Shot; brand:Props['brand']}> = ({shot:s,brand}) => {
  const fr = useCurrentFrame();
  const duration = Math.max(1,s.end-s.start-1);
  const [ink,paint,tint] = themes[brand][s.layout%5];
  const light = s.layout%2 === 1;
  const accent = light ? paint : tint;
  const backdrop = light ? `linear-gradient(${49+s.layout*15}deg,#fffaee,${tint})` :
    `radial-gradient(ellipse at ${18+(s.layout*23)%70}% ${26+(s.layout*17)%50}%,${paint},${ink} 72%)`;
  const dx = (s.layout%2 ? -1:1)*interpolate(fr,[0,duration],[-28,28]);
  const media = {width:'100%',height:'100%',objectFit:s.footage?'cover' as const:'contain' as const,
    transform:`translateX(${dx}px) scale(${1.12+fr/duration*.15})`};
  const crop = [{top:521,left:114,width:852,height:757},{top:553,left:162,width:741,height:653},
    {top:574,left:112,width:855,height:643},{top:517,left:131,width:690,height:760},{top:536,left:216,width:735,height:669}][s.layout%5];
  return <AbsoluteFill style={{background:backdrop,color:light?ink:'#fffbf3',fontFamily:'DejaVu Sans,sans-serif'}}>
    <div style={{position:'absolute',top:225,left:112,right:112,fontWeight:700,fontSize:28,letterSpacing:4,color:accent}}>
      {brand==='tarih'?'TARİHİN BİLİNMEYEN GERÇEKLERİ':'GÜZELLİK VE KİŞİSEL BAKIM'}</div>
    <div style={{position:'absolute',top:287,left:112,right:112,fontFamily:'DejaVu Serif,serif',lineHeight:1.07,fontSize:68}}>{s.title}</div>
    <div style={{position:'absolute',top:472,left:112,width:150+480*fr/duration,height:6,background:accent}} />
    <div style={{position:'absolute',...crop,overflow:'hidden',border:`2px solid ${tint}88`,borderRadius:35,background:paint}}>
      {s.footage ? <OffthreadVideo src={staticFile(s.footage)} muted playbackRate={s.rate} style={media} /> :
        s.image ? <Img src={staticFile(s.image)} style={media} /> :
        <AbsoluteFill style={{padding:58,gap:22,alignItems:'center',justifyContent:'center',display:'flex',
          flexDirection:s.layout%3===2?'row':'column',transform:`translateX(${dx*.8}px) scale(${1+.18*fr/duration})`}}>
          {s.proof.map((point,i)=><div key={`${i}-${point}`} style={{padding:23,fontWeight:700,fontSize:37,
            lineHeight:1.12,minHeight:82,alignContent:'center',textAlign:'center',color:tint,
            width:s.layout%3===2?'31%':`${90-i*4}%`,border:`2px solid ${tint}90`,
            borderRadius:24,background:i%2?ink:paint,opacity:interpolate(fr,[i*9,i*9+19],[.20,1],
            {extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>{point}</div>)}
        </AbsoluteFill>}
    </div>
    <div style={{position:'absolute',top:1303,left:115,right:115,fontSize:25,lineHeight:1.25,color:accent}}>
      <div style={{fontWeight:700,letterSpacing:1.4}}>{s.label}</div><div>{s.credit}</div></div>
  </AbsoluteFill>;
};

const Reel:React.FC<Props> = ({brand,shots,captions}) => {
  const fr=useCurrentFrame(), at=fr/fps;
  const caption=captions.find(item=>item.start<=at&&at<item.end);
  const active=caption?.wordStarts.reduce((index,start,i)=>start<=at?i:index,-1);
  return <AbsoluteFill>
    {shots.map(s=><Sequence key={s.id} from={s.start} durationInFrames={s.end-s.start}><Scene brand={brand} shot={s}/></Sequence>)}
    {caption&&<div style={{position:'absolute',top:1457,left:106,right:106,padding:'14px 24px',minHeight:78,
      background:'#100e13',color:'#fff9e8',borderRadius:24,fontFamily:'DejaVu Sans,sans-serif',fontWeight:700,
      fontSize:45,lineHeight:1.15,textAlign:'center'}}>{caption.text.split(' ').map((word,i)=><React.Fragment key={i}>
        <span style={{color:i===active?'#ffdc8f':'#fff9e8'}}>{word}</span>{' '}</React.Fragment>)}</div>}
  </AbsoluteFill>;
};

const Root:React.FC=()=> <Composition id="DailyReel15G" component={Reel} width={1080} height={1920} fps={fps}
  durationInFrames={1} schema={schema} defaultProps={{brand:'tarih',frames:2100,shots:[],captions:[]}}
  calculateMetadata={({props})=>({durationInFrames:props.frames})}/>;
registerRoot(Root);
