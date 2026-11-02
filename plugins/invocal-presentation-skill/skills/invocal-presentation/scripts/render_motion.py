#!/usr/bin/env python3
"""Portable deterministic chart/motion renderer; consumes prepared global word cues.

Output uses pipeline.py's render-states contract, one state per video frame.
Charts use declared, fixed scales. Values never overshoot. No fabricated data.
"""
import argparse, json, math, io, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def progress(t, start, duration, easing='smooth'):
    if duration <= 0: raise ValueError('Motion duration must be positive')
    p = max(0., min(1., (t-start)/duration))
    if easing == 'linear': return p
    if easing == 'smooth': return p*p*(3-2*p)
    raise ValueError('Unsupported easing: '+easing)


def validate_chart(c):
    if c['kind'] not in ('bar','line'): raise ValueError('Chart kind must be bar or line')
    vals=c['values']; labels=c['labels']; lo,hi=c['domain']
    if not vals or len(vals)!=len(labels): raise ValueError('Chart labels/data lengths differ')
    if not all(math.isfinite(float(v)) and lo<=v<=hi for v in vals) or not lo<hi:
        raise ValueError('Invalid chart values/domain')
    if c['kind']=='bar' and lo!=0: raise ValueError('Bar chart baseline must be zero')
    if c['kind']=='bar' and any(v<0 for v in vals): raise ValueError('Negative bars not supported')
    ticks=c.get('ticks',[lo,hi])
    if len(ticks)<2 or ticks!=sorted(set(ticks)) or ticks[0]!=lo or ticks[-1]!=hi:
        raise ValueError('Ticks must increase and include domain endpoints')
    if len(c['reveals'])!=len(vals): raise ValueError('Each data point needs a reveal cue')
    if c['reveals']!=sorted(c['reveals']): raise ValueError('Point cues must be chronological')
    if c['kind']=='line' and len(set(c['reveals']))!=len(vals): raise ValueError('Line point cues must be distinct')
    if c.get('duration',.65)<=0: raise ValueError('Chart duration must be positive')
    if not c.get('source'): raise ValueError('Chart data provenance is required')


def draw_frame(m, scene, t):
    w,h=m['resolution']; sw,sh=m.get('slide_size',[1280,720]); scale=w/sw
    im=Image.new('RGB',(w,h),scene.get('background','#F6F4EE')); d=ImageDraw.Draw(im)
    def font(size,bold=False):
        return ImageFont.truetype(m.get('font_bold_file' if bold else 'font_file', '/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'),round(size*scale))
    def text(x,y,s,size=26,color='#173C42',bold=False,anchor=None):
        d.text((x*scale,y*scale),str(s),font=font(size,bold),fill=color,anchor=anchor)
    def line(points,color='#D6DEDB',width=1):
        d.line([(x*scale,y*scale) for x,y in points],fill=color,width=max(1,round(width*scale)))
    for el in scene.get('elements',[]):
        if t<el['time'] or (el.get('until') is not None and t>=el['until']): continue
        x,y,ew,eh=el['position']; motion=el.get('motion',{})
        p=progress(t,el['time'],motion.get('duration',.55),motion.get('easing','smooth')) if motion else 1
        if motion.get('kind')=='slide':
            dx,dy=motion.get('offset',[0,25]);x+=dx*(1-p);y+=dy*(1-p)
        if el['type']=='text':
            size=el.get('font_size',28)
            if d.textlength(el['text'],font=font(size,el.get('bold',False)))>ew*scale:
                raise ValueError('Text overflows width: '+el['id'])
            text(x,y,el['text'],size,el.get('color','#173C42'),el.get('bold',False))
        elif el['type']=='outline':
            d.rectangle((x*scale,y*scale,(x+ew)*scale,(y+eh)*scale),outline=el.get('color','#C95029'),width=round(3*scale))
        else: raise ValueError('Motion adapter supports text, outline and charts; use still adapter for images')
    for c in scene.get('charts',[]):
        x,y,cw,ch=c['position'];lo,hi=c['domain'];n=len(c['values'])
        px=x+65; py=y+35; pw=cw-100; ph=ch-100
        Y=lambda v:py+ph*(1-(v-lo)/(hi-lo))
        text(x,y-30,c.get('unit',''),20)
        for v in c.get('ticks',[lo,hi]):
            line([(px,Y(v)),(px+pw,Y(v))]);text(px-15,Y(v),f'{v:g}',19,anchor='rm')
        line([(px,py),(px,py+ph),(px+pw,py+ph)],'#6B817E',2)
        if c['kind']=='bar':
            bw=pw/n*.46
            for i,(label,v,at) in enumerate(zip(c['labels'],c['values'],c['reveals'])):
                cx=px+pw*(i+.5)/n; text(cx,py+ph+19,label,23,anchor='mt')
                if t<at:continue
                p=progress(t,at,c.get('duration',.65));top=Y(v*p)
                d.rectangle(((cx-bw/2)*scale,top*scale,(cx+bw/2)*scale,Y(0)*scale),fill=c.get('colors',['#E56D42','#328D88','#254D73'])[i%len(c.get('colors',['#E56D42','#328D88','#254D73']))])
                if p==1:text(cx,top-13,f'{v:g}',28,bold=True,anchor='mb')
        else:
            X=lambda i:px+pw*i/max(1,n-1)
            for i,label in enumerate(c['labels']):text(X(i),py+ph+19,label,23,anchor='mt')
            pts=[]
            for i,(v,at) in enumerate(zip(c['values'],c['reveals'])):
                if t<at:break
                if i==0:pts.append((X(0),Y(v)));continue
                # The next point is reached at its spoken cue; interpolation is explicitly visual.
                p=progress(t,c['reveals'][i-1],at-c['reveals'][i-1],'linear')
                pts.append((X(i),Y(v)))
            k=sum(t>=at for at in c['reveals'])-1
            if 0<=k<n-1:
                p=progress(t,c['reveals'][k],c['reveals'][k+1]-c['reveals'][k],'linear')
                pts.append((X(k)+(X(k+1)-X(k))*p,Y(c['values'][k])+(Y(c['values'][k+1])-Y(c['values'][k]))*p))
            if len(pts)>1:line(pts,c.get('color','#328D88'),5)
            for i,(v,at) in enumerate(zip(c['values'],c['reveals'])):
                if t>=at:
                    xx,yy=X(i)*scale,Y(v)*scale;r=6*scale
                    d.ellipse((xx-r,yy-r,xx+r,yy+r),fill='#173C42');text(X(i),Y(v)-18,f'{v:g}',25,bold=True,anchor='mb')
            if pts:
                xx,yy=pts[-1];r=9*scale
                d.ellipse(((xx-r)*scale,(yy-r)*scale,(xx+r)*scale,(yy+r)*scale),fill='#E56D42')
        focus=c.get('focus')
        if focus and focus['start']<=t<focus['end']:
            yy=Y(focus.get('value',0));line([(px,yy),(px+pw,yy)],'#E56D42',4)
            text(px+pw,y-30,focus['label'],20,'#B44123',anchor='rt')
        text(x,y+ch+8,c['source'],17,'#5A706D')
    return im


def render(manifest, out):
    m=json.loads(Path(manifest).read_text());out=Path(out);out.mkdir()
    for s in m['scenes']:
        for c in s.get('charts',[]):
            validate_chart(c)
            x,y,w,h=c['position'];sw,sh=m.get('slide_size',[1280,720])
            if min(x,y)<0 or w<250 or h<200 or x+w>sw or y+h+40>sh:raise ValueError('Chart geometry exceeds safe canvas')
            if any(at<s['start'] or at>=s['end'] for at in c['reveals']):raise ValueError('Chart cue outside scene')
    states=[]
    previous_bytes=None
    previous_scene=None
    previous_image=None
    transition_image=None
    transition_start=0
    for i in range(math.ceil(m['duration']*m['fps'])):
        t=i/m['fps'];s=next(s for s in m['scenes'] if s['start']<=t<s['end'])
        image=draw_frame(m,s,t)
        if previous_scene is not None and previous_scene!=s['id']:
            transition_image=previous_image.copy(); transition_start=t
        transition=m.get('motion_transition_seconds',.24)
        if transition_image is not None and transition>0 and t-transition_start<transition:
            image=Image.blend(transition_image,image,progress(t,transition_start,transition))
        data=image.tobytes()
        if data!=previous_bytes or previous_scene!=s['id']:
            p=out/f'frame-{i:06}.png'
            buffer=io.BytesIO();image.save(buffer,format='PNG');payload=buffer.getvalue()
            temporary=Path(str(p)+'.tmp')
            with temporary.open('wb') as f:
                f.write(payload);f.flush();os.fsync(f.fileno())
            os.replace(temporary,p)
            if p.stat().st_size!=len(payload):raise ValueError('Incomplete frame write')
            states.append({'scene':s['id'],'time':t,'path':str(p.resolve()),'transition_seconds':0})
        previous_bytes=data;previous_scene=s['id'];previous_image=image
    (out/'render-states.json').write_text(json.dumps(states,indent=2))
    print(json.dumps({'frames':len(states),'states':str(out/'render-states.json')}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');a=p.parse_args();render(a.manifest,a.output)
