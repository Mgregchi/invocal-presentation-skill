#!/usr/bin/env node
// Optional Work adapter. Read the host Presentations skill and current API docs first.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [manifestArg, outArg] = process.argv.slice(2);
if (!manifestArg || !outArg) throw new Error('Usage: render_work.mjs MANIFEST.json NEW_RENDER_DIRECTORY');
const require = createRequire(import.meta.url);
let modulePath;
try { modulePath = require.resolve('@oai/artifact-tool', {paths: [process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES || '', process.cwd()]}); }
catch { throw new Error('The supplied @oai/artifact-tool runtime is unavailable. Use the host presentation renderer and produce render-states.json.'); }
const {Presentation, PresentationFile} = await import(pathToFileURL(modulePath).href);
const manifest = JSON.parse(await fs.readFile(path.resolve(manifestArg),'utf8'));
const out = path.resolve(outArg);
await fs.mkdir(out); // Deliberately reject an existing revision.
const [width,height]=manifest.slide_size||[1280,720];
const presentation=Presentation.create({slideSize:{width,height}});
const scale=manifest.resolution[0]/width;
if (Math.abs(height*scale-manifest.resolution[1])>.01) throw new Error('Slide and video aspect ratios differ');
const states=[];
const geometries=[];
for (const scene of manifest.scenes) {
  const slide=presentation.slides.add();
  slide.background.fill=scene.background||'#FAF9F6';
  const objects=new Map();
  const events=[{time:scene.start}];
  for(const element of scene.elements){
    events.push({time:element.time,add:element});
    if(element.until!==null)events.push({time:element.until,remove:element.id});
  }
  events.sort((a,b)=>a.time-b.time);
  for(let index=0;index<events.length;){
    const time=events[index].time;
    while(index<events.length && Math.abs(events[index].time-time)<1e-7){
      const event=events[index++];
      if(event.remove){
        const shape=objects.get(event.remove);
        if(!shape)throw new Error('Unknown focus marker');
        shape.line={style:'solid',fill:'none',width:0};
      }
      if(event.add){
        const el=event.add;
        const [left,top,w,h]=el.position;
        const position={left,top,width:w,height:h};
        if(el.type==='image'){
          const bytes=await fs.readFile(el.src);
          const contentType=el.src.toLowerCase().endsWith('.png')?'image/png':el.src.toLowerCase().endsWith('.svg')?'image/svg+xml':'image/jpeg';
          slide.images.add({blob:bytes,contentType,position,fit:el.fit||'contain',alt:el.alt||el.attribution});
        }else{
          const shape=slide.shapes.add({name:el.id,geometry:el.type==='outline'?'rect':'textbox',position,
            fill:'none',line:{style:'solid',fill:el.type==='outline'?(el.color||'#A13F64'):'none',width:el.type==='outline'?(el.line_width||4):0}});
          if(el.type==='text'){
            shape.text=el.text;
            shape.text.style={typeface:el.font||manifest.font||'DejaVu Sans',fontSize:el.font_size||28,
              color:el.color||'#173C42',bold:!!el.bold,wrap:'word',insets:0,verticalAlignment:'top'};
            geometries.push({scene:scene.id,id:el.id,text:el.text,position,font_size:el.font_size||28});
          }
          objects.set(el.id,shape);
        }
      }
    }
    if(time<scene.end){
      const file=path.join(out,`state-${String(states.length).padStart(4,'0')}.png`);
      const png=await presentation.export({slide,format:'png',scale});
      await fs.writeFile(file,new Uint8Array(await png.arrayBuffer()));
      states.push({scene:scene.id,time,path:file});
    }
  }
  const sec=manifest.sections.find(s=>s.id===scene.section);
  const spoken=sec?sec.words.filter(w=>sec.start+w.start>=scene.start && sec.start+w.start<scene.end).map(w=>w.text).join(' '):'';
  slide.speakerNotes.text=`${scene.title||scene.id}\nVideo ${scene.start.toFixed(3)}–${scene.end.toFixed(3)} s\n\nNARRATION\n${spoken}\n\n${scene.notes||''}\n\nSOURCES\n${[...(manifest.sources||[]),...(sec?.sources||[])].join('\n')}\n\nIMAGE ATTRIBUTION\n${scene.elements.filter(e=>e.type==='image').map(e=>e.attribution).join('\n')}`;
  const png=await presentation.export({slide,format:'png',scale});
  await fs.writeFile(path.join(out,`slide-${String(presentation.slides.items.length).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(out,'candidate.pptx');
await(await PresentationFile.exportPptx(presentation)).save(candidate);
await fs.writeFile(path.join(out,'render-states.json'),JSON.stringify(states,null,2));
await fs.writeFile(path.join(out,'geometry.json'),JSON.stringify(geometries,null,2));
console.log(JSON.stringify({candidate_pptx:candidate,states:path.join(out,'render-states.json'),slides:manifest.scenes.length,
  next:'Render/review all slides and complete the host Presentations skill finalization. Candidate export alone is not approval.'},null,2));
